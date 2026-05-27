import logging

from flask import Flask

import db
from config import FLASK_SECRET_KEY
from routes.api import api_bp
from routes.auth import auth_bp
from routes.search import search_bp
from utils.log_config import setup_logging

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    setup_logging()

    app = Flask(__name__)
    app.secret_key = FLASK_SECRET_KEY

    db.init_db()
    logger.info("Database initialised")

    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(api_bp)
    logger.info("Blueprints registered")

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info("Starting server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
