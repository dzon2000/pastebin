from datetime import datetime, timedelta, timezone

from app import create_app


def test_create_and_read_json_paste(tmp_path):
    app = create_app(tmp_path / "pastes.db")
    client = app.test_client()

    response = client.post("/api/pastes", json={"text": "hello from curl"})

    assert response.status_code == 201
    url = response.json["url"]
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    assert "-" in slug
    assert client.get(f"/{slug}").get_data(as_text=True) == "hello from curl"


def test_editor_is_available(tmp_path):
    response = create_app(tmp_path / "pastes.db").test_client().get("/")

    assert response.status_code == 200
    assert b'id="paste-text"' in response.data
    assert b'id="create-paste"' in response.data


def test_create_accepts_plain_text(tmp_path):
    app = create_app(tmp_path / "pastes.db")
    response = app.test_client().post(
        "/api/pastes", data="line one\nline two", content_type="text/plain"
    )

    assert response.status_code == 201


def test_rejects_empty_and_unsupported_payloads(tmp_path):
    client = create_app(tmp_path / "pastes.db").test_client()

    assert client.post("/api/pastes", json={"text": ""}).status_code == 400
    assert client.post("/api/pastes", json={"content": "wrong field"}).status_code == 415
    assert client.post("/api/pastes", data="text/html", content_type="text/html").status_code == 415


def test_expired_paste_is_not_served(tmp_path):
    current_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    app = create_app(tmp_path / "pastes.db", clock=lambda: current_time)
    client = app.test_client()
    slug = client.post("/api/pastes", json={"text": "temporary"}).json["url"].rsplit("/", 1)[-1]

    current_time += timedelta(hours=24)

    assert client.get(f"/{slug}").status_code == 404
