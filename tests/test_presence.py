from time import sleep
from uuid import uuid4

from app.permissions.presence_permissions import can_view_presence
from app.presence.manager import PresenceManager
from app.presence.typing_manager import TypingManager
from app.schemas.message import MAX_MESSAGE_LENGTH


def test_presence_manager_tracks_first_and_final_connection():
    manager = PresenceManager()
    user_id = uuid4()
    assert manager.register(user_id, "socket-a")
    assert manager.is_online(user_id)
    assert manager.get_connection_count(user_id) == 1
    assert not manager.register(user_id, "socket-b")
    assert manager.get_connection_count(user_id) == 2
    assert manager.unregister("socket-a") == (user_id, False)
    assert manager.is_online(user_id)
    assert manager.unregister("socket-b") == (user_id, True)
    assert not manager.is_online(user_id)


def test_presence_manager_ignores_unknown_disconnect():
    manager = PresenceManager()
    assert manager.unregister("unknown") == (None, False)


def test_typing_manager_keeps_user_typing_until_all_sources_stop():
    manager = TypingManager(timeout_seconds=1)
    user_id, context_id = uuid4(), uuid4()
    callback_keys = []
    assert manager.start(user_id, "socket-a", "channel", context_id, callback_keys.append)
    assert not manager.start(user_id, "socket-b", "channel", context_id, callback_keys.append)
    assert not manager.stop(user_id, "socket-a", "channel", context_id)
    assert manager.is_typing(user_id, "channel", context_id)
    assert manager.stop(user_id, "socket-b", "channel", context_id)
    assert not manager.is_typing(user_id, "channel", context_id)


def test_typing_manager_timeout_cleans_state():
    manager = TypingManager(timeout_seconds=0.01)
    user_id, context_id = uuid4(), uuid4()
    callback_keys = []
    manager.start(user_id, "socket-a", "conversation", context_id, callback_keys.append)
    sleep(0.05)
    assert callback_keys == [(user_id, "conversation", context_id)]
    assert not manager.is_typing(user_id, "conversation", context_id)


def test_typing_cleanup_returns_only_last_sources():
    manager = TypingManager(timeout_seconds=1)
    user_id, context_id = uuid4(), uuid4()
    manager.start(user_id, "socket-a", "channel", context_id, lambda key: None)
    manager.start(user_id, "socket-b", "channel", context_id, lambda key: None)
    assert manager.cleanup_socket("socket-a") == []
    assert manager.cleanup_socket("socket-b") == [(user_id, "channel", context_id)]


def test_presence_policy_allows_self_only_without_shared_context(monkeypatch):
    viewer = type("User", (), {"id": uuid4()})()
    target = type("User", (), {"id": uuid4()})()
    monkeypatch.setattr(
        "app.permissions.presence_permissions._can_view_presence",
        lambda viewer_id, target_id: viewer_id == target_id,
    )
    assert can_view_presence(viewer, viewer)
    assert not can_view_presence(viewer, target)


def test_message_limit_constant_remains_independent_of_presence():
    assert MAX_MESSAGE_LENGTH == 4000
