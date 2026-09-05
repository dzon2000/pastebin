from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from flask import Flask, Response, jsonify, render_template, request

PASTE_LIFETIME = timedelta(hours=24)
MAX_PASTE_SIZE = 1_000_000

WORDS = (
    "amber", "apple", "autumn", "bamboo", "blue", "breeze", "cedar", "citrus",
    "cloud", "coral", "cosmic", "crystal", "daisy", "dawn", "drift", "ember",
    "falcon", "fern", "firefly", "forest", "fox", "glimmer", "grove", "harbor",
    "hazel", "honey", "island", "jade", "jasmine", "jupiter", "maple", "meadow",
    "misty", "moon", "moss", "ocean", "olive", "orchid", "pebble", "pine",
    "plum", "polar", "rabbit", "rain", "raven", "river", "robin", "saffron",
    "sage", "salmon", "shadow", "sky", "snow", "solar", "sparrow", "spring",
    "stone", "summer", "sunset", "thistle", "thunder", "tiger", "valley",
    "velvet", "violet", "willow", "winter", "wren",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _create_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS pastes (
            slug TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def _new_slug() -> str:
    return "-".join(secrets.choice(WORDS).strip() for _ in range(3))


def _paste_text() -> str | None:
    if request.is_json:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            return None
        return payload["text"]
    if request.mimetype == "text/plain":
        return request.get_data(as_text=True)
    return None


def create_app(
    database_path: str | os.PathLike[str] | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> Flask:
    app = Flask(__name__)
    path = Path(database_path or os.environ.get("PASTEBIN_DATABASE", "data/pastes.db"))
    app.config["DATABASE_PATH"] = path
    app.config["CLOCK"] = clock

    @app.get("/")
    def editor() -> str:
        return render_template("index.html")

    @app.post("/api/pastes")
    def create_paste() -> Response:
        content = _paste_text()
        if content is None:
            return jsonify(error="Send JSON with a string 'text' field or a text/plain body."), 415
        if not content:
            return jsonify(error="Paste text must not be empty."), 400
        if len(content.encode("utf-8")) > MAX_PASTE_SIZE:
            return jsonify(error=f"Paste text must be at most {MAX_PASTE_SIZE} bytes."), 413

        created_at = app.config["CLOCK"]()
        expires_at = created_at + PASTE_LIFETIME
        connection = _create_database(path)
        try:
            for _ in range(10):
                slug = _new_slug()
                try:
                    connection.execute(
                        "INSERT INTO pastes (slug, content, created_at, expires_at) VALUES (?, ?, ?, ?)",
                        (slug, content, _timestamp(created_at), _timestamp(expires_at)),
                    )
                    connection.commit()
                    break
                except sqlite3.IntegrityError:
                    continue
            else:
                return jsonify(error="Could not allocate a paste URL. Try again."), 503
        finally:
            connection.close()

        return jsonify(url=request.host_url.rstrip("/") + "/" + slug), 201

    @app.get("/<slug>")
    def read_paste(slug: str) -> Response:
        connection = _create_database(path)
        try:
            paste = connection.execute(
                "SELECT content, expires_at FROM pastes WHERE slug = ?", (slug,)
            ).fetchone()
            if paste is None:
                return jsonify(error="Paste not found."), 404
            if _parse_timestamp(paste["expires_at"]) <= app.config["CLOCK"]():
                connection.execute("DELETE FROM pastes WHERE slug = ?", (slug,))
                connection.commit()
                return jsonify(error="Paste not found."), 404
            return Response(paste["content"], mimetype="text/plain")
        finally:
            connection.close()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
