"""Tiny offline card app. Week 12 intentionally leaves /api/stats red."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Red Before Green")
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"


def ensure_database():
    created = not DB_PATH.exists()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL)")
        if created:
            db.executemany("INSERT INTO cards (title, status) VALUES (?, ?)", [
                ("Write tests", "done"), ("Lock red", "done"), ("Implement", "todo"), ("Review", "todo")])


@contextmanager
def database():
    ensure_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


@app.get("/")
def home():
    return {"app": "Red Before Green", "docs": "/docs"}


@app.get("/cards")
def cards():
    with database() as db:
        return [dict(row) for row in db.execute("SELECT * FROM cards ORDER BY id")]


@app.post("/cards", status_code=201)
def create_card(title: str, status: str = "todo"):
    with database() as db:
        cursor = db.execute("INSERT INTO cards (title, status) VALUES (?, ?)", (title, status))
    return {"id": cursor.lastrowid, "title": title, "status": status}


@app.get("/api/stats")
def stats():
    raise HTTPException(status_code=501, detail="Write tests first; feature missing")
