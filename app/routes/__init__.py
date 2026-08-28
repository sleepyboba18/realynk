from flask import Flask

from app.routes.auth import auth_bp
from app.routes.attachments import attachments_bp
from app.routes.channels import channels_bp
from app.routes.conversations import conversations_bp
from app.routes.health import health_bp
from app.routes.messages import messages_bp
from app.routes.notifications import notifications_bp
from app.routes.presence import presence_bp
from app.routes.reactions import reactions_bp
from app.routes.reads import reads_bp
from app.routes.users import users_bp


def register_routes(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(attachments_bp)
    app.register_blueprint(channels_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(presence_bp)
    app.register_blueprint(reactions_bp)
    app.register_blueprint(reads_bp)
