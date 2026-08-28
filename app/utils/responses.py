from flask import jsonify


def success_response(data: object, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def error_response(code: str, message: str, status: int, details: dict[str, str] | None = None):
    error: dict[str, object] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return jsonify({"success": False, "error": error}), status
