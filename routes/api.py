import logging

import flask
from flask import Blueprint, jsonify, request, session

import db
import utils.session_manager as session_manager

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/job/<job_id>")
def job_status(job_id: str) -> tuple[flask.Response, int]:
    job = db.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    logger.debug("Job %s polled — status: %s", job_id[:8], job["status"])
    return jsonify(job), 200


@api_bp.route("/job/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id: str) -> tuple[flask.Response, int]:
    key = session.get("session_key")
    if not key or not session_manager.get(key):
        return jsonify({"error": "Not logged in"}), 401
    db.cancel_job(job_id)
    logger.info("Job %s cancelled by user", job_id[:8])
    return jsonify({"ok": True}), 200


@api_bp.route("/confirm", methods=["POST"])
def confirm_match() -> tuple[flask.Response, int]:
    key = session.get("session_key")
    if not key or not session_manager.get(key):
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    an_id = data.get("an_id", "").strip()
    as_id = data.get("as_id", "").strip()
    if not an_id or not as_id:
        return jsonify({"error": "Both an_id and as_id are required"}), 400

    db.save_confirmed_match(an_id, as_id)
    logger.info("Match confirmed: AN/%s <-> AS/%s", an_id, as_id)
    return jsonify({"ok": True}), 200
