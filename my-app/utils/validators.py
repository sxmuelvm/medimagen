"""Validaciones de entrada. Cada funcion devuelve el valor limpio o lanza ErrorNegocio con un mensaje claro."""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from utils.errors import ErrorNegocio

_CEDULA = re.compile(r"\d{10}")
_CORREO = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_TELEFONO = re.compile(r"\d{7,15}")
_USUARIO = re.compile(r"[A-Za-z0-9._\-]{4,50}")


def texto(valor, etiqueta, maximo=255, minimo=1, obligatorio=True):
    limpio = " ".join(str(valor or "").split())
    if not limpio:
        if obligatorio:
            raise ErrorNegocio(f"{etiqueta} es obligatorio.")
        return None
    if len(limpio) < minimo or len(limpio) > maximo:
        raise ErrorNegocio(f"{etiqueta} debe tener entre {minimo} y {maximo} caracteres.")
    return limpio


def cedula(valor, etiqueta="La cédula"):
    limpio = str(valor or "").strip()
    if not _CEDULA.fullmatch(limpio):
        raise ErrorNegocio(f"{etiqueta} debe tener exactamente 10 dígitos.")
    return limpio


def correo(valor, obligatorio=True, etiqueta="El correo"):
    limpio = str(valor or "").strip().lower()
    if not limpio:
        if obligatorio:
            raise ErrorNegocio(f"{etiqueta} es obligatorio.")
        return None
    if len(limpio) > 100 or not _CORREO.fullmatch(limpio):
        raise ErrorNegocio(f"{etiqueta} no es válido.")
    return limpio


def telefono(valor, obligatorio=False, etiqueta="El teléfono"):
    limpio = str(valor or "").strip()
    if not limpio:
        if obligatorio:
            raise ErrorNegocio(f"{etiqueta} es obligatorio.")
        return None
    if not _TELEFONO.fullmatch(limpio):
        raise ErrorNegocio(f"{etiqueta} debe tener entre 7 y 15 dígitos.")
    return limpio


def nombre_usuario(valor):
    limpio = str(valor or "").strip()
    if not _USUARIO.fullmatch(limpio):
        raise ErrorNegocio("El nombre de usuario debe tener de 4 a 50 caracteres: letras, números, punto, guion o guion bajo.")
    return limpio


def entero(valor, etiqueta, minimo=None, maximo=None):
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ErrorNegocio(f"{etiqueta} debe ser un número entero.") from None
    if (minimo is not None and numero < minimo) or (maximo is not None and numero > maximo):
        raise ErrorNegocio(f"{etiqueta} está fuera del rango permitido.")
    return numero


def decimal(valor, etiqueta, minimo=Decimal("0"), maximo=Decimal("99999999.99")):
    try:
        numero = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise ErrorNegocio(f"{etiqueta} debe ser un número.") from None
    if not numero.is_finite() or numero < minimo or numero > maximo:
        raise ErrorNegocio(f"{etiqueta} está fuera del rango permitido.")
    return numero.quantize(Decimal("0.01"))


def fecha(valor, etiqueta="La fecha"):
    try:
        return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ErrorNegocio(f"{etiqueta} no es válida.") from None


def fecha_laborable(valor, etiqueta="La fecha"):
    dia = fecha(valor, etiqueta)
    if dia.weekday() >= 5:
        raise ErrorNegocio("Las citas solo se agendan de lunes a viernes.")
    return dia


def hora_bloque(valor):
    """Devuelve 'HH:00:00' si es un inicio de bloque valido (07:00 a 17:00, en punto)."""
    try:
        h = datetime.strptime(str(valor).strip()[:5], "%H:%M")
    except ValueError:
        raise ErrorNegocio("La hora no es válida.") from None
    if h.minute != 0 or not 7 <= h.hour <= 17:
        raise ErrorNegocio("La hora debe ser un bloque de una hora entre las 07:00 y las 17:00.")
    return h.strftime("%H:00:00")


def opcion(valor, permitidos, etiqueta):
    limpio = str(valor or "").strip()
    if limpio not in permitidos:
        raise ErrorNegocio(f"{etiqueta} no es válido.")
    return limpio


def clave_segura(clave, cedula_usuario=None):
    """Politica minima: 8 a 128 caracteres, con letras y numeros, distinta de la cedula."""
    if not isinstance(clave, str) or len(clave) < 8:
        raise ErrorNegocio("La contraseña debe tener al menos 8 caracteres.")
    if len(clave) > 128:
        raise ErrorNegocio("La contraseña no puede superar 128 caracteres.")
    if not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
        raise ErrorNegocio("La contraseña debe incluir letras y números.")
    if cedula_usuario and clave == cedula_usuario:
        raise ErrorNegocio("La contraseña no puede ser igual a la cédula.")
    return clave


def no_futura(valor, etiqueta="La fecha"):
    if valor > date.today():
        raise ErrorNegocio(f"{etiqueta} no puede ser futura.")
    return valor