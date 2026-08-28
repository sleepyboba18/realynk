from math import ceil
from uuid import UUID

from flask import Blueprint, g, request

from app.auth.decorators import auth_required
from app.permissions.channel_permissions import can_view_channel
from app.repositories import channel_repository
from app.schemas.channel import (
    validate_create_channel,
    validate_role,
    validate_update_channel,
    validate_user_id,
)
from app.services import channel_service, membership_service
from app.utils.responses import error_response, success_response


channels_bp = Blueprint("channels", __name__, url_prefix="/api/v1/channels")


def _pagination() -> tuple[int, int] | tuple[None, tuple[object, int]]:
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return None, error_response("VALIDATION_ERROR", "Invalid pagination", 422, {"page": "Must be an integer"})
    if page < 1 or per_page < 1 or per_page > 100:
        return None, error_response(
            "VALIDATION_ERROR", "Invalid pagination", 422, {"per_page": "Must be between 1 and 100"}
        )
    return page, per_page


def _channel_id(value: str) -> UUID | tuple[None, tuple[object, int]]:
    try:
        return UUID(value)
    except ValueError:
        return None, error_response("CHANNEL_NOT_FOUND", "Channel not found", 404)


def _domain_error(error: channel_service.ChannelError):
    return error_response(error.code, error.message, error.status)


@channels_bp.post("")
@auth_required
def create_channel():
    data = request.get_json(silent=True)
    errors = validate_create_channel(data)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    channel = channel_service.create_channel(
        g.current_user.id,
        data["name"],
        data.get("description"),
        data.get("is_private", False),
    )
    membership = channel_repository.get_membership(channel.id, g.current_user.id)
    return success_response(channel.to_dict(membership), 201)


@channels_bp.get("")
@auth_required
def list_channels():
    page, per_page = _pagination()
    if page is None:
        return per_page
    items, total = channel_repository.list_channels(g.current_user.id, page, per_page)
    return success_response(
        {
            "items": [channel.to_dict() for channel in items],
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": ceil(total / per_page)},
        }
    )


@channels_bp.get("/<channel_id>")
@auth_required
def get_channel(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    try:
        channel, membership = channel_service.get_channel_for_user(parsed, g.current_user.id)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response(channel.to_dict(membership))


@channels_bp.patch("/<channel_id>")
@auth_required
def update_channel(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    try:
        channel, membership = channel_service.get_channel_for_user(parsed, g.current_user.id)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    data = request.get_json(silent=True)
    errors = validate_update_channel(data)
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    if not data:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, {"body": "At least one field is required"})
    try:
        channel = channel_service.update_channel(channel, membership, data)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response(channel.to_dict(channel_repository.get_membership(channel.id, g.current_user.id)))


@channels_bp.delete("/<channel_id>")
@auth_required
def delete_channel(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    try:
        channel, membership = channel_service.get_channel_for_user(parsed, g.current_user.id)
        channel_service.delete_channel(channel, membership)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response({"message": "Channel deleted"})


@channels_bp.post("/<channel_id>/join")
@auth_required
def join_channel(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    channel = channel_repository.get_channel(parsed)
    if channel is None:
        return error_response("CHANNEL_NOT_FOUND", "Channel not found", 404)
    try:
        membership = membership_service.join_public(channel, g.current_user.id)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response(membership.to_dict(), 201)


@channels_bp.post("/<channel_id>/leave")
@auth_required
def leave_channel(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    channel = channel_repository.get_channel(parsed)
    if channel is None:
        return error_response("CHANNEL_NOT_FOUND", "Channel not found", 404)
    try:
        membership_service.leave(channel, g.current_user.id)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response({"message": "Left channel"})


@channels_bp.get("/<channel_id>/members")
@auth_required
def list_members(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    try:
        channel, membership = channel_service.get_channel_for_user(parsed, g.current_user.id)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    page, per_page = _pagination()
    if page is None:
        return per_page
    items, total = channel_repository.list_members(channel.id, page, per_page)
    return success_response(
        {
            "items": [item.to_dict() for item in items],
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": ceil(total / per_page)},
        }
    )


@channels_bp.post("/<channel_id>/members")
@auth_required
def add_member(channel_id: str):
    parsed = _channel_id(channel_id)
    if isinstance(parsed, tuple):
        return parsed[1]
    errors = validate_user_id(request.get_json(silent=True))
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    channel = channel_repository.get_channel(parsed)
    if channel is None:
        return error_response("CHANNEL_NOT_FOUND", "Channel not found", 404)
    try:
        membership = membership_service.add_member(channel, g.current_user.id, UUID(request.json["user_id"]))
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response(membership.to_dict(), 201)


@channels_bp.patch("/<channel_id>/members/<user_id>")
@auth_required
def update_member_role(channel_id: str, user_id: str):
    parsed_channel = _channel_id(channel_id)
    if isinstance(parsed_channel, tuple):
        return parsed_channel[1]
    try:
        target_id = UUID(user_id)
    except ValueError:
        return error_response("MEMBERSHIP_NOT_FOUND", "Membership not found", 404)
    errors = validate_role(request.get_json(silent=True))
    if errors:
        return error_response("VALIDATION_ERROR", "Invalid request", 422, errors)
    channel = channel_repository.get_channel(parsed_channel)
    if channel is None:
        return error_response("CHANNEL_NOT_FOUND", "Channel not found", 404)
    try:
        membership = membership_service.change_role(channel, g.current_user.id, target_id, request.json["role"])
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response(membership.to_dict())


@channels_bp.delete("/<channel_id>/members/<user_id>")
@auth_required
def remove_member(channel_id: str, user_id: str):
    parsed_channel = _channel_id(channel_id)
    if isinstance(parsed_channel, tuple):
        return parsed_channel[1]
    try:
        target_id = UUID(user_id)
    except ValueError:
        return error_response("MEMBERSHIP_NOT_FOUND", "Membership not found", 404)
    channel = channel_repository.get_channel(parsed_channel)
    if channel is None:
        return error_response("CHANNEL_NOT_FOUND", "Channel not found", 404)
    try:
        membership_service.remove_member(channel, g.current_user.id, target_id)
    except channel_service.ChannelError as error:
        return _domain_error(error)
    return success_response({"message": "Member removed"})
