"""Reportes para el administrador: ingresos por area y por mes (solo citas atendidas)."""
import re
from decimal import Decimal

from conexion.conexionBD import consultar
from utils.constants import CUENTA_ADMINISTRADOR
from utils.errors import ErrorNegocio

_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _mes_o_none(valor, etiqueta):
    texto = str(valor or "").strip()
    if not texto:
        return None
    if not _MES.match(texto):
        raise ErrorNegocio(f"{etiqueta} no es válido (formato AAAA-MM).")
    return texto


def ingresos(usuario, desde=None, hasta=None, area=None):
    """Ingresos por area y mes, con totales por area, por mes y general. `desde` y `hasta` son 'AAAA-MM'."""
    desde, hasta = _mes_o_none(desde, "El mes inicial"), _mes_o_none(hasta, "El mes final")
    if desde and hasta and desde > hasta:
        raise ErrorNegocio("El mes inicial no puede ser posterior al mes final.")
    condiciones, parametros = [], []
    if desde:
        condiciones.append("mes >= %s")
        parametros.append(desde)
    if hasta:
        condiciones.append("mes <= %s")
        parametros.append(hasta)
    areas = [f["nombre"] for f in consultar(CUENTA_ADMINISTRADOR, "SELECT nombre FROM area ORDER BY id_area",
                                            id_usuario_app=usuario)]
    area = area if area in areas else None
    if area:
        condiciones.append("area = %s")
        parametros.append(area)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    filas = consultar(CUENTA_ADMINISTRADOR, f"""
        SELECT area, mes, citas_atendidas, ingresos FROM v_reporte_ingresos {donde}
        ORDER BY mes DESC, area""", parametros, id_usuario_app=usuario)

    por_area, por_mes = {}, {}
    for f in filas:
        a = por_area.setdefault(f["area"], {"area": f["area"], "citas": 0, "ingresos": Decimal("0")})
        m = por_mes.setdefault(f["mes"], {"mes": f["mes"], "citas": 0, "ingresos": Decimal("0")})
        for acumulado in (a, m):
            acumulado["citas"] += int(f["citas_atendidas"])
            acumulado["ingresos"] += f["ingresos"]
    total = {"citas": sum(x["citas"] for x in por_area.values()),
             "ingresos": sum((x["ingresos"] for x in por_area.values()), Decimal("0"))}
    return {"filas": filas, "por_area": list(por_area.values()),
            "por_mes": sorted(por_mes.values(), key=lambda x: x["mes"]), "total": total, "areas": areas,
            "filtros": {"desde": desde or "", "hasta": hasta or "", "area": area or ""}}