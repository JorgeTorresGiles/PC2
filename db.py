"""Acceso SQLite: una conexion por solicitud y cierre automatico."""
import sqlite3
from pathlib import Path
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db_path = Path(current_app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    schema_path = Path(current_app.root_path) / "schema.sql"
    db.executescript(schema_path.read_text(encoding="utf-8"))
    existe = db.execute("SELECT id FROM usuarios WHERE usuario = ?", ("admin",)).fetchone()
    if existe is None:
        # Credenciales EXCLUSIVAMENTE para esta practica local, exigidas por el enunciado.
        db.execute("INSERT INTO usuarios (usuario, password_hash) VALUES (?, ?)",
                   ("admin", generate_password_hash("123")))
    db.commit()
