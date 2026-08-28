from app import create_app


def test_health_endpoints_are_available():
    app = create_app()
    client = app.test_client()

    live = client.get("/health/live")
    ready = client.get("/health/ready")
    health = client.get("/health")

    assert live.status_code == 200
    assert live.get_json()["status"] == "ok"
    assert ready.status_code == 200
    assert health.status_code == 200


def test_requests_include_correlation_id_header():
    app = create_app()
    client = app.test_client()

    response = client.get("/health/live")

    assert response.headers.get("X-Request-ID")
