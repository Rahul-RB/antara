import logging
import sys


def setup_logging() -> None:
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove any handlers already attached (e.g. from previous calls)
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("urllib3", "requests", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
