import logging
import uuid

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue

import utils.session_manager as session_manager
from scrapers.an_scraper import AnuragaScraper
from scrapers.as_scraper import AseemaScraper

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page() -> ResponseReturnValue:
    if session.get("session_key") and session_manager.get(session["session_key"]):
        return redirect(url_for("search.search_page"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login() -> ResponseReturnValue:
    an_username = request.form.get("an_username", "").strip()
    an_password = request.form.get("an_password", "").strip()
    as_email = request.form.get("as_email", "").strip()
    as_password = request.form.get("as_password", "").strip()

    if not all([an_username, an_password, as_email, as_password]):
        flash("All fields are required.")
        return render_template("login.html"), 400

    logger.info("Login attempt — AN user: %s, AS email: %s", an_username, as_email)

    an_scraper = AnuragaScraper()
    an_ok = an_scraper.login(username=an_username, password=an_password)
    if not an_ok:
        logger.warning("Anuraga login failed for user: %s", an_username)
        flash("Anuraga login failed. Check username/password.")
        return render_template("login.html"), 401
    logger.info("Anuraga login successful: %s", an_username)

    as_scraper = AseemaScraper()
    as_ok = as_scraper.login(email=as_email, password=as_password)
    if not as_ok:
        logger.warning("Aseema login failed for email: %s", as_email)
        flash("Aseema login failed. Check email/password.")
        return render_template("login.html"), 401
    logger.info("Aseema login successful: %s (app_no=%s)", as_email, as_scraper._app_no)

    key = str(uuid.uuid4())
    session_manager.store(
        key,
        {
            "an_session": an_scraper._session,
            "as_session": as_scraper._session,
            "an_username": an_username,
            "an_password": an_password,
            "as_email": as_email,
            "as_password": as_password,
            "as_app_no": as_scraper._app_no,
            "as_user_email": as_scraper._user_email,
        },
    )
    session["session_key"] = key
    logger.info("Session created: %s", key[:8])
    return redirect(url_for("search.search_page"))


@auth_bp.route("/logout")
def logout() -> ResponseReturnValue:
    key = session.pop("session_key", None)
    if key:
        session_manager.remove(key)
        logger.info("Session removed: %s", key[:8])
    return redirect(url_for("auth.login_page"))
