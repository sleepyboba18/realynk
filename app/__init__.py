import logging
from http import HTTPStatus

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.extensions import db, migrate, socketio
from app.middleware.observability import register_observability_middleware
from app.middleware.security import register_security_middleware
from app.models import Attachment, Channel, ChannelMembership, Conversation, ConversationParticipant, Message, MessageRead, MessageReaction, ModerationAction, Notification, NotificationPreference, RateLimitBucket, SecurityEvent, User  # noqa: F401
from app.observability.logger import configure_logging
from app.routes import register_routes
import app.sockets  # noqa: F401


logger = logging.getLogger(__name__)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        response = {
            "success": False,
            "error": {
                "code": error.name.upper().replace(" ", "_"),
                "message": error.description,
            },
        }
        return jsonify(response), error.code or HTTPStatus.INTERNAL_SERVER_ERROR

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logger.exception("Unexpected application error", exc_info=error)
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                },
            }
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def create_app() -> Flask:
    settings = Config.from_environment()
    configure_logging(settings.log_level, settings.log_format)
    logger.info("Configuration loaded: %s", settings.sanitized_summary())

    app = Flask(__name__)
    app.config.from_mapping(settings.flask_settings())

    cors_origins = settings.cors_origins
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins, "methods": settings.cors_allowed_methods, "allow_headers": settings.cors_allowed_headers}},
        supports_credentials=settings.cors_allow_credentials,
    )
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(
        app,
        async_mode=app.config["SOCKETIO_ASYNC_MODE"],
        cors_allowed_origins=cors_origins,
        max_http_buffer_size=settings.socketio_max_http_buffer_size,
        logger=False,
        engineio_logger=False,
    )

    register_observability_middleware(app)
    register_security_middleware(app)
    _register_error_handlers(app)
    register_routes(app)
    logger.info("Configured %s application", settings.app_name)
    return app
