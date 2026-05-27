import hashlib
import logging
import os
from typing import Any

import cv2
import numpy as np
import pillow_heif
import requests
from PIL import Image

from config import IMAGE_CACHE_DIR, REQUEST_TIMEOUT, USER_AGENT
from db import get_cached_embeddings, save_image_cache

logger = logging.getLogger(__name__)

_face_app = None


def _get_app() -> Any:
    global _face_app
    if _face_app is None:
        logger.info("Loading InsightFace buffalo_l model (first run may take a moment)...")
        from insightface.app import FaceAnalysis

        _face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded")
    return _face_app


def download_image(url: str, requests_session: requests.Session | None = None) -> str | None:
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = url.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    local_path = os.path.join(IMAGE_CACHE_DIR, f"{url_hash}.{ext}")

    if os.path.exists(local_path):
        logger.debug("Image cache hit: %s", url)
        return local_path

    logger.debug("Downloading image: %s", url)
    try:
        if requests_session:
            resp = requests_session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        else:
            resp = requests.get(
                url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}, stream=True
            )
        if resp.status_code != 200:
            logger.warning("Image download failed (HTTP %d): %s", resp.status_code, url)
            return None
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        logger.debug("Image saved: %s", local_path)
        return local_path
    except Exception as e:
        logger.warning("Image download error (%s): %s", url, e)
        return None


def _read_image(image_path: str) -> np.ndarray | None:
    img = cv2.imread(image_path)
    if img is not None:
        return img
    try:
        pillow_heif.register_heif_opener()
        pil_img = Image.open(image_path).convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def get_embeddings(image_path: str) -> list[list[float]]:
    img = _read_image(image_path)
    if img is None:
        logger.warning("Could not read image: %s", image_path)
        return []
    try:
        app = _get_app()
        faces = app.get(img)
        logger.debug("Detected %d face(s) in %s", len(faces), os.path.basename(image_path))
        return [face.normed_embedding.tolist() for face in faces]
    except Exception as e:
        logger.warning("Face detection error on %s: %s", image_path, e)
        return []


def best_similarity(embeddings_a: list[list[float]], embeddings_b: list[list[float]]) -> float:
    if not embeddings_a or not embeddings_b:
        return 0.0
    best = -1.0
    for ea in embeddings_a:
        for eb in embeddings_b:
            sim = float(np.dot(np.array(ea), np.array(eb)))
            if sim > best:
                best = sim
    return best


def similarity_to_confidence(similarity: float) -> float:
    return round((similarity + 1) / 2 * 100, 2)


def get_or_compute_embeddings(
    site: str,
    profile_id: str,
    image_urls: list[str],
    requests_session: requests.Session | None = None,
) -> list[list[float]]:
    cached = get_cached_embeddings(site, profile_id)
    cached_urls = {r["image_url"] for r in cached}
    all_embeddings = [r["embedding"] for r in cached]

    if cached:
        logger.debug("%s/%s: %d embedding(s) from cache", site.upper(), profile_id, len(cached))

    new_count = 0
    for url in image_urls:
        if url in cached_urls:
            continue
        local_path = download_image(url, requests_session)
        if not local_path:
            save_image_cache(site, profile_id, url, None, None)
            continue
        embs = get_embeddings(local_path)
        save_image_cache(site, profile_id, url, local_path, embs[0] if embs else None)
        all_embeddings.extend(embs)
        new_count += 1

    if new_count:
        logger.debug("%s/%s: computed %d new embedding(s)", site.upper(), profile_id, new_count)

    return all_embeddings
