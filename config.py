import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "antara.db")
IMAGE_CACHE_DIR = os.path.join(BASE_DIR, "images")

FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-prod")

AN_BASE_URL = "https://www.anuragamatrimony.com"
AS_BASE_URL = "https://aseemamatrimony.in"

FACE_SIMILARITY_THRESHOLD = 0.4

DEFAULT_HEIGHT_MIN_CM = 152  # 5'0" — used when a profile has no height
DEFAULT_HEIGHT_MAX_CM = 170  # 5'7"
TOP_N_RESULTS = 6  # best + 5 others shown to user

REQUEST_TIMEOUT = 120  # seconds
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
)
