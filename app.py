"""Practica Calificada 2: control web de gastos personales.
Autor: Jorge Antonio Torres Giles
Stack: Python, Flask, SQLite, Jinja2, HTML, CSS, JavaScript.
Demostracion local. Usuario inicial solicitado: admin / 123.
"""
from datetime import date, timedelta
from functools import wraps
import csv
import hmac
import io
import os
from pathlib import Path
import secrets

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, Response, session, url_for)
from werkzeug.security import check_password_hash

from db import close_db, get_db, init_db
from validaciones import (importe, monto_a_centimos, validar_descripcion,
                          validar_fecha, validar_filtros)


def crear_app(config_test=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    archivo_clave = Path(app.instance_path) / ".secret_key"
    if not archivo_clave.exists():
        # Es persistente para que la sesion no se invalide al reiniciar el servidor.
        archivo_clave.write_text(secrets.token_hex(32), encoding="utf-8")
    clave = os.environ.get("FLASK_SECRET_KEY") or archivo_clave.read_text(encoding="utf-8").strip()
    app.config.update(
        SECRET_KEY=clave,
        DATABASE=str(Path(app.instance_path) / "gastos.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1_000_000,
    )
    if config_test:
        app.config.update(config_test)

    app.teardown_appcontext(close_db)
    app.jinja_env.filters["dinero"] = importe

    @app.before_request
    def preparar_solicitud():
        g.usuario = None
        uid = session.get("usuario_id")
        if uid is not None:
            g.usuario = get_db().execute(
                "SELECT id, usuario FROM usuarios WHERE id = ?", (uid,)
            ).fetchone()
            if g.usuario is None:
                session.clear()
        # Validacion CSRF en TODAS las operaciones que modifican datos.
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            entregado = request.form.get("csrf_token", "")
            esperado = session.get("csrf_token", "")
            if not esperado or not hmac.compare_digest(esperado, entregado):
                abort(400, description="Solicitud rechazada: token de seguridad invalido.")

    @app.context_processor
    def contexto_global():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]
        return {"csrf_token": csrf_token, "usuario_actual": g.get("usuario"),
                "fecha_hoy": date.today().isoformat()}

    def login_requerido(func):
        @wraps(func)
        def protegida(*args, **kwargs):
            if g.usuario is None:
                flash("Debes iniciar sesion para acceder.", "warning")
                return redirect(url_for("login"))
            return func(*args, **kwargs)
        return protegida

    def filtros_busqueda():
        desde = request.args.get("desde", "").strip()
        hasta = request.args.get("hasta", "").strip()
        try:
            return validar_filtros(desde, hasta)
        except ValueError as error:
            flash(str(error), "danger")
            return None

    def condiciones(usuario_id, desde="", hasta=""):
        condiciones_sql = ["usuario_id = ?"]
        parametros = [usuario_id]
        if desde:
            condiciones_sql.append("fecha >= ?")
            parametros.append(desde)
        if hasta:
            condiciones_sql.append("fecha <= ?")
            parametros.append(hasta)
        return " AND ".join(condiciones_sql), parametros

    @app.route("/")
    def inicio():
        return redirect(url_for("dashboard" if g.usuario is not None else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.usuario is not None:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            usuario = request.form.get("usuario", "").strip()
            clave = request.form.get("clave", "")
            registro = get_db().execute("SELECT * FROM usuarios WHERE usuario = ?",
                                        (usuario,)).fetchone()
            if registro and check_password_hash(registro["password_hash"], clave):
                session.clear()
                session["usuario_id"] = registro["id"]
                session.permanent = True
                flash("Bienvenido, admin. Has iniciado sesion correctamente.", "success")
                return redirect(url_for("dashboard"))
            flash("Usuario o contrasena incorrectos.", "danger")
        return render_template("login.html", titulo="Iniciar sesion")

    @app.post("/logout")
    @login_requerido
    def logout():
        session.clear()
        flash("Sesion cerrada correctamente.", "info")
        return redirect(url_for("login"))

    @app.get("/dashboard")
    @login_requerido
    def dashboard():
        uid = g.usuario["id"]
        hoy = date.today()
        mes = hoy.strftime("%Y-%m")
        totales = get_db().execute(
            """SELECT COUNT(*) AS cantidad, COALESCE(SUM(monto_centimos),0) AS total,
                      COALESCE(AVG(monto_centimos),0) AS promedio,
                      COALESCE(SUM(CASE WHEN substr(fecha,1,7) = ? THEN monto_centimos ELSE 0 END), 0) AS mes
               FROM gastos WHERE usuario_id = ?""", (mes, uid)
        ).fetchone()
        ultimos = get_db().execute(
            "SELECT * FROM gastos WHERE usuario_id = ? ORDER BY fecha DESC,id DESC LIMIT 6", (uid,)
        ).fetchall()
        mensuales = get_db().execute(
            """SELECT substr(fecha,1,7) AS mes, SUM(monto_centimos) AS total
               FROM gastos WHERE usuario_id = ? GROUP BY substr(fecha,1,7)
               ORDER BY mes DESC LIMIT 6""", (uid,)
        ).fetchall()
        mayor = max((r["total"] for r in mensuales), default=1)
        return render_template("dashboard.html", titulo="Panel principal", totales=totales,
                               ultimos=ultimos, mensuales=mensuales, mayor=mayor)

    @app.get("/gastos")
    @login_requerido
    def gastos():
        datos = get_db().execute(
            "SELECT * FROM gastos WHERE usuario_id = ? ORDER BY fecha DESC,id DESC", (g.usuario["id"],)
        ).fetchall()
        return render_template("gastos.html", titulo="Mis gastos", gastos=datos)

    @app.route("/gastos/nuevo", methods=["GET", "POST"])
    @login_requerido
    def nuevo_gasto():
        datos = {"fecha": date.today().isoformat(), "descripcion": "", "monto": ""}
        if request.method == "POST":
            datos = {k: request.form.get(k, "") for k in datos}
            try:
                fecha = validar_fecha(datos["fecha"])
                descripcion = validar_descripcion(datos["descripcion"])
                centimos = monto_a_centimos(datos["monto"])
            except ValueError as error:
                flash(str(error), "danger")
            else:
                db = get_db()
                db.execute(
                    "INSERT INTO gastos (fecha, descripcion, monto_centimos, usuario_id) VALUES (?, ?, ?, ?)",
                    (fecha, descripcion, centimos, g.usuario["id"])
                )
                db.commit()
                flash("Gasto registrado correctamente.", "success")
                return redirect(url_for("gastos"))
        return render_template("form_gasto.html", titulo="Registrar gasto", datos=datos, editando=False)

    @app.route("/gastos/<int:gasto_id>/editar", methods=["GET", "POST"])
    @login_requerido
    def editar_gasto(gasto_id):
        registro = get_db().execute("SELECT * FROM gastos WHERE id = ? AND usuario_id = ?",
                                    (gasto_id, g.usuario["id"])).fetchone()
        if registro is None:
            abort(404)
        datos = {"fecha": registro["fecha"], "descripcion": registro["descripcion"],
                 "monto": f'{registro["monto_centimos"] / 100:.2f}'}
        if request.method == "POST":
            datos = {k: request.form.get(k, "") for k in datos}
            try:
                fecha = validar_fecha(datos["fecha"])
                descripcion = validar_descripcion(datos["descripcion"])
                centimos = monto_a_centimos(datos["monto"])
            except ValueError as error:
                flash(str(error), "danger")
            else:
                db = get_db()
                db.execute(
                    "UPDATE gastos SET fecha = ?, descripcion = ?, monto_centimos = ? "
                    "WHERE id = ? AND usuario_id = ?",
                    (fecha, descripcion, centimos, gasto_id, g.usuario["id"])
                )
                db.commit()
                flash("Gasto actualizado correctamente.", "success")
                return redirect(url_for("gastos"))
        return render_template("form_gasto.html", titulo="Editar gasto", datos=datos,
                               editando=True, gasto_id=gasto_id)

    @app.post("/gastos/<int:gasto_id>/eliminar")
    @login_requerido
    def eliminar_gasto(gasto_id):
        db = get_db()
        resultado = db.execute("DELETE FROM gastos WHERE id = ? AND usuario_id = ?",
                               (gasto_id, g.usuario["id"]))
        db.commit()
        if not resultado.rowcount:
            abort(404)
        flash("Gasto eliminado correctamente.", "success")
        return redirect(url_for("gastos"))

    @app.get("/reportes")
    @login_requerido
    def reportes():
        filtros = filtros_busqueda()
        if filtros is None:
            return redirect(url_for("reportes"))
        desde, hasta = filtros
        where, params = condiciones(g.usuario["id"], desde, hasta)
        db = get_db()
        filas = db.execute(f"SELECT * FROM gastos WHERE {where} ORDER BY fecha DESC,id DESC", params).fetchall()
        resumen = db.execute(
            f"SELECT COUNT(*) AS cantidad, COALESCE(SUM(monto_centimos),0) AS total, "
            f"COALESCE(AVG(monto_centimos),0) AS promedio FROM gastos WHERE {where}", params
        ).fetchone()
        por_mes = db.execute(
            f"SELECT substr(fecha,1,7) AS mes, COUNT(*) AS cantidad, SUM(monto_centimos) AS total "
            f"FROM gastos WHERE {where} GROUP BY substr(fecha,1,7) ORDER BY mes DESC", params
        ).fetchall()
        return render_template("reportes.html", titulo="Reporte de gastos", gastos=filas,
                               resumen=resumen, por_mes=por_mes, desde=desde, hasta=hasta)

    @app.get("/reportes/csv")
    @login_requerido
    def exportar_csv():
        filtros = filtros_busqueda()
        if filtros is None:
            return redirect(url_for("reportes"))
        desde, hasta = filtros
        where, params = condiciones(g.usuario["id"], desde, hasta)
        filas = get_db().execute(
            f"SELECT fecha, descripcion, monto_centimos FROM gastos WHERE {where} ORDER BY fecha DESC,id DESC",
            params
        ).fetchall()
        salida = io.StringIO()
        escritor = csv.writer(salida, delimiter=";")
        escritor.writerow(["Fecha", "Descripcion", "Monto (S/)"])
        for fila in filas:
            descripcion = fila["descripcion"]
            # Evitar interpretacion como formulas al abrir un CSV en Excel.
            if descripcion.lstrip().startswith(("=", "+", "-", "@")):
                descripcion = "'" + descripcion
            escritor.writerow([fila["fecha"], descripcion, f'{fila["monto_centimos"] / 100:.2f}'])
        contenido = "\ufeff" + salida.getvalue()
        return Response(contenido, mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=reporte_gastos.csv"})

    @app.errorhandler(400)
    def error_400(error):
        return render_template("error.html", titulo="Solicitud invalida", codigo=400,
                               mensaje="La solicitud no pudo procesarse por motivos de seguridad o validacion."), 400

    @app.errorhandler(404)
    def error_404(error):
        return render_template("error.html", titulo="Pagina no encontrada", codigo=404,
                               mensaje="La pagina solicitada no existe o el registro no esta disponible."), 404

    with app.app_context():
        init_db()
    return app


app = crear_app()

if __name__ == "__main__":
    # El servidor integrado es exclusivamente para pruebas locales.
    app.run(host="127.0.0.1", port=5000, debug=False)
