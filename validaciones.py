"""Reglas de validacion reutilizables, independientes de Flask."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

MONTO_MAX_CENTIMOS = 100_000_000_00  # S/ 100 millones, limite practico de demostracion


def validar_fecha(texto):
    """Devuelve ISO yyyy-mm-dd o lanza ValueError."""
    texto = (texto or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        raise ValueError("Indica una fecha valida en formato AAAA-MM-DD.")
    try:
        fecha = date.fromisoformat(texto)
    except ValueError as error:
        raise ValueError("La fecha indicada no existe.") from error
    return fecha.isoformat()


def validar_descripcion(texto):
    texto = " ".join((texto or "").split())
    if not (3 <= len(texto) <= 160):
        raise ValueError("La descripcion debe tener entre 3 y 160 caracteres.")
    if any(ord(c) < 32 for c in texto):
        raise ValueError("La descripcion contiene caracteres no permitidos.")
    return texto


def monto_a_centimos(texto):
    """Convierte '12.50' o '12,50' a 1250, sin errores de coma flotante."""
    texto = (texto or "").strip().replace(",", ".")
    if len(texto) > 12 or not re.fullmatch(r"\d+(?:\.\d{1,2})?", texto):
        raise ValueError("El monto debe ser positivo y tener como maximo dos decimales.")
    try:
        monto = Decimal(texto)
        centimos = int((monto * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, OverflowError) as error:
        raise ValueError("El monto no es valido.") from error
    if not 0 < centimos <= MONTO_MAX_CENTIMOS:
        raise ValueError("Ingresa un monto mayor que cero y dentro del limite permitido.")
    return centimos


def validar_filtros(desde, hasta):
    desde = validar_fecha(desde) if desde else ""
    hasta = validar_fecha(hasta) if hasta else ""
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha inicial no puede ser mayor que la final.")
    return desde, hasta


def importe(centimos):
    return f"{int(centimos) / 100:,.2f}"
