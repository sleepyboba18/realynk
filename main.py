import logging
import sys

from app import create_app
from app.config import ConfigurationError
from app.extensions.socketio import socketio


def main() -> None:
    try:
        app = create_app()
    except ConfigurationError as exc:
        logging.getLogger(__name__).error("Configuration error: %s", exc)
        raise SystemExit(1) from None

    logging.getLogger(__name__).info("Starting Realynk")
    socketio.run(
        app,
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )


if __name__ == "__main__":
    main()
