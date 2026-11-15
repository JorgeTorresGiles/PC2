"""Pruebas de integracion con Flask test_client. No alteran la base real."""
import io
import os
import tempfile
import unittest
from pathlib import Path

from app import crear_app
from db import get_db


class GastosWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        ruta = str(Path(self.temp.name) / "prueba.db")
        self.app = crear_app({"TESTING": True, "DATABASE": ruta, "SECRET_KEY": "test-session-key"})
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def csrf(self):
        self.cliente.get("/login")
        with self.cliente.session_transaction() as s:
            return s["csrf_token"]

    def entrar(self, clave="123"):
        token = self.csrf()
        return self.cliente.post("/login", data={"csrf_token": token,
                                                  "usuario": "admin", "clave": clave},
                                 follow_redirects=True)

    def registrar(self, monto="25.50", descripcion="Pago de Internet", fecha="2026-11-08"):
        with self.cliente.session_transaction() as s:
            token = s["csrf_token"]
        return self.cliente.post("/gastos/nuevo", data={"csrf_token": token, "fecha": fecha,
                                                       "descripcion": descripcion, "monto": monto},
                                 follow_redirects=True)

    def test_redireccion_sin_sesion(self):
        r = self.cliente.get("/dashboard")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_inicio_sesion_correcto(self):
        r = self.entrar()
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Panel principal", r.data)

    def test_inicio_sesion_erroneo(self):
        r = self.entrar("error")
        self.assertIn(b"incorrectos", r.data)
        self.assertEqual(self.cliente.get("/dashboard").status_code, 302)

    def test_registrar_y_reportar(self):
        self.entrar()
        r = self.registrar()
        self.assertIn(b"Gasto registrado correctamente", r.data)
        reporte = self.cliente.get("/reportes")
        self.assertIn(b"25.50", reporte.data)
        self.assertIn(b"Pago de Internet", reporte.data)
        with self.app.app_context():
            fila = get_db().execute("SELECT monto_centimos FROM gastos").fetchone()
            self.assertEqual(fila["monto_centimos"], 2550)

    def test_monto_negativo_rechazado(self):
        self.entrar()
        r = self.registrar("-7")
        self.assertIn(b"positivo", r.data)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM gastos").fetchone()[0], 0)

    def test_csrf_obligatorio(self):
        self.entrar()
        r = self.cliente.post("/gastos/nuevo", data={"fecha": "2026-11-08",
                                                      "descripcion": "Prueba de CSRF", "monto": "10"})
        self.assertEqual(r.status_code, 400)

    def test_reporte_filtrado(self):
        self.entrar()
        self.registrar(fecha="2026-11-08")
        self.registrar(fecha="2026-10-15", monto="12")
        r = self.cliente.get("/reportes?desde=2026-11-01&hasta=2026-11-30")
        self.assertIn(b"25.50", r.data)
        self.assertNotIn(b"12.00", r.data)

    def test_exportar_csv(self):
        self.entrar()
        self.registrar()
        r = self.cliente.get("/reportes/csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers["Content-Type"])
        self.assertIn("Pago de Internet", r.data.decode("utf-8-sig"))

    def test_editar_y_borrar(self):
        self.entrar()
        self.registrar()
        with self.app.app_context():
            gasto_id = get_db().execute("SELECT id FROM gastos").fetchone()["id"]
        with self.cliente.session_transaction() as s:
            token = s["csrf_token"]
        r = self.cliente.post(f"/gastos/{gasto_id}/editar", data={"csrf_token": token,
             "fecha": "2026-11-09", "descripcion": "Pago actualizado", "monto": "35"}, follow_redirects=True)
        self.assertIn(b"Gasto actualizado", r.data)
        r = self.cliente.post(f"/gastos/{gasto_id}/eliminar", data={"csrf_token": token}, follow_redirects=True)
        self.assertIn(b"Gasto eliminado", r.data)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM gastos").fetchone()[0], 0)

    def test_logout(self):
        self.entrar()
        with self.cliente.session_transaction() as s:
            token = s["csrf_token"]
        r = self.cliente.post("/logout", data={"csrf_token": token}, follow_redirects=True)
        self.assertIn(b"Iniciar sesi", r.data)
        self.assertEqual(self.cliente.get("/dashboard").status_code, 302)


if __name__ == '__main__':
    unittest.main()
