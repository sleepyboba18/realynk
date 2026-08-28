from flask_migrate import Migrate

from app.extensions.database import db
from app.extensions.socketio import socketio

migrate = Migrate()

__all__ = ["db", "migrate", "socketio"]
