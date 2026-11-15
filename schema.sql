-- Practica Calificada 2 - Gestion de gastos personales (Flask + SQLite)
-- El campo monto_centimos evita errores de redondeo al sumar importes monetarios.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    descripcion TEXT NOT NULL CHECK (length(trim(descripcion)) BETWEEN 3 AND 160),
    monto_centimos INTEGER NOT NULL CHECK (monto_centimos > 0),
    usuario_id INTEGER NOT NULL,
    creado_en TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gastos_usuario_fecha ON gastos (usuario_id, fecha DESC);
