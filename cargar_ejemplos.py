"""Datos FICTICIOS opcionales para mostrar el reporte; no modifica gastos ya existentes."""
from datetime import date, timedelta
from app import app
from db import get_db


def insertar_demostracion():
    hoy = date.today()
    datos = [
        (0, "Compra de alimentos", 6450),
        (2, "Pasajes de transporte", 1200),
        (5, "Materiales de estudio", 3990),
        (12, "Pago de Internet", 7990),
        (35, "Articulos de limpieza", 2875),
        (48, "Servicios del hogar", 11500),
        (66, "Compra de utiles", 2250),
    ]
    with app.app_context():
        db = get_db()
        cantidad = db.execute("SELECT COUNT(*) FROM gastos").fetchone()[0]
        if cantidad:
            print("No se insertaron ejemplos porque ya existen gastos en la base de datos.")
            return
        uid = db.execute("SELECT id FROM usuarios WHERE usuario = ?", ("admin",)).fetchone()[0]
        db.executemany("INSERT INTO gastos (fecha,descripcion,monto_centimos,usuario_id) VALUES (?,?,?,?)",
                       [((hoy - timedelta(days=d)).isoformat(), desc, centimos, uid)
                        for d, desc, centimos in datos])
        db.commit()
        print(f"Se insertaron {len(datos)} gastos ficticios. Actualiza /dashboard o /reportes.")


if __name__ == "__main__":
    insertar_demostracion()
