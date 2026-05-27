import logging
import re

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue

import db
import jobs
import utils.session_manager as session_manager

logger = logging.getLogger(__name__)

search_bp = Blueprint("search", __name__)


def _detect_site(profile_id: str) -> str | None:
    pid = profile_id.strip()
    if re.match(r"^AGM\d+$", pid, re.IGNORECASE):
        return "an"
    if re.match(r"^[A-Z]{2}\d+/\d+$", pid):
        return "as"
    return None


def _require_session() -> str | None:
    key = session.get("session_key")
    if not key or not session_manager.get(key):
        return None
    return key


@search_bp.route("/")
def index() -> ResponseReturnValue:
    key = _require_session()
    if not key:
        return redirect(url_for("auth.login_page"))
    return redirect(url_for("search.search_page"))


@search_bp.route("/search", methods=["GET"])
def search_page() -> ResponseReturnValue:
    key = _require_session()
    if not key:
        return redirect(url_for("auth.login_page"))
    return render_template("search.html")


@search_bp.route("/search", methods=["POST"])
def start_search() -> ResponseReturnValue:
    key = _require_session()
    if not key:
        return jsonify({"error": "Not logged in"}), 401

    profile_id = request.json.get("profile_id", "").strip()
    if not profile_id:
        return jsonify({"error": "Profile ID is required"}), 400

    source_site = _detect_site(profile_id)
    if not source_site:
        logger.warning("Could not detect site for ID: %s", profile_id)
        return jsonify(
            {
                "error": "Could not detect site from ID. "
                "AN IDs start with AGM (e.g. AGM000000), "
                "AS IDs look like SB000/00."
            }
        ), 400

    logger.info("Search request — %s/%s", source_site.upper(), profile_id)

    existing = db.get_confirmed_match(source_site, profile_id)
    if existing:
        logger.info("Cache hit for %s/%s -> %s", source_site.upper(), profile_id, existing)
        return jsonify({"cached": True, "match": existing, "source_site": source_site})

    job_id = jobs.submit_job(source_site, profile_id, key)
    return jsonify({"job_id": job_id, "source_site": source_site})
