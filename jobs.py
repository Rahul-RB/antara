import logging
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import db
import utils.session_manager as session_manager
from config import FACE_SIMILARITY_THRESHOLD, TOP_N_RESULTS
from matcher import best_similarity, get_or_compute_embeddings, similarity_to_confidence
from scrapers import get_scraper
from scrapers.as_scraper import AseemaScraper

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1)


def submit_load_profile_job(source_site: str, source_id: str, session_key: str) -> str:
    job_id = str(uuid.uuid4())
    db.create_job(job_id, source_site, source_id)
    logger.info("Load-profile job %s submitted — %s/%s", job_id[:8], source_site.upper(), source_id)
    _executor.submit(_run_load_profile_job, job_id, source_site, source_id, session_key)
    return job_id


def _run_load_profile_job(job_id: str, source_site: str, source_id: str, session_key: str) -> None:
    short = job_id[:8]
    logger.info("[%s] Load-profile job started", short)
    db.update_job(job_id, "running")
    try:
        session_data = session_manager.get(session_key)
        if not session_data:
            msg = "Session expired. Please log in again."
            logger.warning("[%s] %s", short, msg)
            db.update_job(job_id, "error", error=msg)
            return

        src_scraper = get_scraper(source_site)
        src_scraper._session = session_data[f"{source_site}_session"]

        logger.info("[%s] Fetching profile %s/%s", short, source_site.upper(), source_id)
        source_profile = src_scraper.get_profile(source_id)
        if not source_profile:
            msg = f"Profile {source_id} not found on {source_site.upper()}."
            logger.warning("[%s] %s", short, msg)
            db.update_job(job_id, "error", error=msg)
            return

        db.upsert_profile(source_site, source_id, source_profile)
        db.update_job(job_id, "done", result={"source": source_profile})
        logger.info("[%s] Load-profile job done", short)

    except Exception:
        tb = traceback.format_exc()
        logger.error("[%s] Load-profile error:\n%s", short, tb)
        db.update_job(job_id, "error", error=tb)


def submit_job(source_site: str, source_id: str, session_key: str) -> str:
    job_id = str(uuid.uuid4())
    db.create_job(job_id, source_site, source_id)
    logger.info("Job %s submitted — %s/%s", job_id[:8], source_site.upper(), source_id)
    _executor.submit(_run_job, job_id, source_site, source_id, session_key)
    return job_id


def _run_job(job_id: str, source_site: str, source_id: str, session_key: str) -> None:
    short = job_id[:8]
    logger.info("[%s] Job started", short)
    db.update_job(job_id, "running")
    try:
        session_data = session_manager.get(session_key)
        if not session_data:
            msg = "Session expired. Please log in again."
            logger.warning("[%s] %s", short, msg)
            db.update_job(job_id, "error", error=msg)
            return

        src_scraper = get_scraper(source_site)
        src_scraper._session = session_data[f"{source_site}_session"]

        target_site = "as" if source_site == "an" else "an"
        tgt_scraper = get_scraper(target_site)
        tgt_scraper._session = session_data[f"{target_site}_session"]
        if target_site == "as":
            assert isinstance(tgt_scraper, AseemaScraper)
            tgt_scraper._app_no = session_data.get("as_app_no")
            tgt_scraper._user_email = session_data.get("as_user_email")

        # Fetch source profile
        logger.info("[%s] Fetching source profile %s/%s", short, source_site.upper(), source_id)
        source_profile = src_scraper.get_profile(source_id)
        if not source_profile:
            msg = f"Profile {source_id} not found on {source_site.upper()}."
            logger.warning("[%s] %s", short, msg)
            db.update_job(job_id, "error", error=msg)
            return

        logger.info(
            "[%s] Source profile: age=%s height=%scm nakshatra=%s rashi=%s",
            short,
            source_profile.get("age"),
            source_profile.get("height_cm"),
            source_profile.get("nakshatra"),
            source_profile.get("rashi"),
        )
        db.upsert_profile(source_site, source_id, source_profile)
        # Write source profile immediately so the frontend can display it while searching
        db.update_job(job_id, "running", result={"source": source_profile, "matches": []})

        if db.is_job_cancelled(job_id):
            logger.info("[%s] Job cancelled", short)
            return

        image_urls = source_profile.get("image_urls") or src_scraper.get_profile_images(
            source_profile
        )
        logger.info("[%s] Source has %d image(s)", short, len(image_urls))

        source_embeddings = get_or_compute_embeddings(
            source_site, source_id, image_urls, src_scraper._session
        )
        if not source_embeddings:
            msg = "No face detected in source profile images."
            logger.warning("[%s] %s", short, msg)
            db.update_job(job_id, "error", error=msg)
            return
        logger.info("[%s] Source embeddings: %d face(s)", short, len(source_embeddings))

        # Search candidates on target site
        age = source_profile.get("age") or 25
        height_cm = source_profile.get("height_cm")
        nakshatra = source_profile.get("nakshatra") or ""
        rashi = source_profile.get("rashi") or ""

        logger.info(
            "[%s] Searching %s — age=%s height=%s nakshatra=%s rashi=%s",
            short,
            target_site.upper(),
            age,
            height_cm,
            nakshatra,
            rashi,
        )
        if target_site == "an":
            gender = source_profile.get("gender", "Female")
            sex = gender if gender in ("Male", "Female") else "Female"
            candidates = tgt_scraper.search_candidates(  # type: ignore[call-arg]
                age=age, height_cm=height_cm, nakshatra=nakshatra, rashi=rashi, sex=sex
            )
        else:
            candidates = tgt_scraper.search_candidates(
                age=age, height_cm=height_cm, nakshatra=nakshatra, rashi=rashi
            )
        logger.info("[%s] Found %d candidate(s) on %s", short, len(candidates), target_site.upper())

        results: list[dict[str, Any]] = []
        for i, candidate in enumerate(candidates):
            if db.is_job_cancelled(job_id):
                logger.info("[%s] Job cancelled during candidate processing", short)
                return
            cand_id = candidate["profile_id"]
            try:
                cand_images = tgt_scraper.get_profile_images(candidate)
                candidate["image_urls"] = cand_images
                logger.debug("[%s] Candidate %s: %d image(s)", short, cand_id, len(cand_images))

                cand_embeddings = get_or_compute_embeddings(
                    target_site, cand_id, cand_images, tgt_scraper._session
                )
                if not cand_embeddings:
                    logger.debug("[%s] No face detected for %s, skipping", short, cand_id)
                    continue

                sim = best_similarity(source_embeddings, cand_embeddings)
                confidence = similarity_to_confidence(sim)
                logger.info(
                    "[%s] %s/%d  %s  sim=%.4f  conf=%.1f%%",
                    short,
                    target_site.upper(),
                    i + 1,
                    cand_id,
                    sim,
                    confidence,
                )
                results.append(
                    {
                        "profile": candidate,
                        "similarity": sim,
                        "confidence": confidence,
                        "same_person": sim >= FACE_SIMILARITY_THRESHOLD,
                    }
                )
                db.upsert_profile(target_site, cand_id, candidate)
            except Exception:
                logger.warning(
                    "[%s] Error processing candidate %s:\n%s",
                    short,
                    cand_id,
                    traceback.format_exc(),
                )
                continue

        results.sort(key=lambda x: x["similarity"], reverse=True)
        logger.info(
            "[%s] Job done. Top match: %s (%.1f%%)",
            short,
            results[0]["profile"]["profile_id"] if results else "none",
            results[0]["confidence"] if results else 0,
        )

        db.update_job(
            job_id,
            "done",
            result={
                "source": source_profile,
                "matches": results[:TOP_N_RESULTS],
            },
        )

    except NotImplementedError as e:
        logger.error("[%s] Not implemented: %s", short, e)
        db.update_job(job_id, "error", error=str(e))
    except Exception:
        tb = traceback.format_exc()
        logger.error("[%s] Unexpected error:\n%s", short, tb)
        db.update_job(job_id, "error", error=tb)
