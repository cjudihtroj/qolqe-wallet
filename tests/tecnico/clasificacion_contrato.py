"""QUÉ ES: lógica de apoyo para las pruebas técnicas de Schemathesis (no es una prueba).

PARA QUÉ: Schemathesis guarda cada solicitud que generó en un archivo HAR. Este módulo
  1. clasifica cada caso según la VALIDACIÓN DE ENTRADA que ejercita (obligatoriedad,
     tipo, rango, cabeceras, método), deducida de lo que dice el contrato OpenAPI de
     POST /api/servicios/pagos: cuerpo {"deuda_id": entero} obligatorio + token Bearer;
  2. decide si la API respondió lo correcto para esa validación;
  3. genera el reporte HTML reportes/schemathesis/ultimo/reporte.html.
Lo usa tests/tecnico/test_contrato_schemathesis.py en cada ejecución de pytest.
"""
import html
import json
from collections import OrderedDict

# Validación → (qué se envía y qué se espera, estados HTTP correctos)
VALIDACIONES = OrderedDict([
    ("Válido según el contrato", ("deuda_id entero positivo con token: decide la regla de negocio", {201, 404, 409})),
    ("Obligatoriedad: falta deuda_id", ("Objeto sin el campo obligatorio (required: deuda_id)", {422})),
    ("Obligatoriedad: sin cuerpo", ("Cuerpo vacío aunque el requestBody es obligatorio", {422})),
    ("Tipo: deuda_id no es entero", ("deuda_id con texto, decimal, booleano, null… (type: integer)", {422})),
    ("Tipo: el cuerpo no es un objeto", ("Cuerpo lista, número, texto o booleano (type: object)", {422})),
    ("Rango: deuda_id cero o negativo", ("Entero ≤ 0: no debe pagar nada", {404, 422})),
    ("Rango: entero enorme (> 64 bits)", ("Entero gigante; el contrato no declara máximo (OBS-01): se rechaza", {422})),
    ("Cabecera: sin token", ("Sin Authorization (security: HTTPBearer)", {401})),
    ("Cabecera: token inválido", ("Authorization alterada", {401})),
    ("Cabecera: sin Content-Type", ("Sin Content-Type: application/json", {422})),
    ("Método HTTP no permitido", ("PUT, PATCH, OPTIONS… en la ruta de pago", {405})),
])


def clasificar(entrada: dict) -> str:
    """Devuelve el nombre de la validación de entrada que ejercita un caso del HAR."""
    solicitud = entrada["request"]
    estado = entrada["response"]["status"]
    cabeceras = {c["name"].lower(): c["value"] for c in solicitud["headers"]}
    cuerpo = solicitud.get("postData", {}).get("text", "")
    if solicitud["method"] != "POST":
        return "Método HTTP no permitido"
    if "authorization" not in cabeceras:
        return "Cabecera: sin token"
    if estado == 401:
        return "Cabecera: token inválido"
    if "content-type" not in cabeceras:
        return "Cabecera: sin Content-Type"
    if cuerpo == "":
        return "Obligatoriedad: sin cuerpo"
    try:
        datos = json.loads(cuerpo)
    except ValueError:
        return "Tipo: el cuerpo no es un objeto"
    if not isinstance(datos, dict):
        return "Tipo: el cuerpo no es un objeto"
    if "deuda_id" not in datos:
        return "Obligatoriedad: falta deuda_id"
    valor = datos["deuda_id"]
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)  # en JSON Schema, 1.0 también es un "integer" válido
    if not isinstance(valor, int) or isinstance(valor, bool):
        return "Tipo: deuda_id no es entero"
    if abs(valor) >= 2**63:
        return "Rango: entero enorme (> 64 bits)"
    if valor <= 0:
        return "Rango: deuda_id cero o negativo"
    return "Válido según el contrato"


def analizar(entradas: list[dict]) -> list[dict]:
    """Un dict por caso: número, validación, método, cuerpo, estado, respuesta y si es correcto."""
    casos = []
    for numero, entrada in enumerate(entradas, 1):
        validacion = clasificar(entrada)
        estado = entrada["response"]["status"]
        texto = entrada["response"]["content"].get("text") or ""
        try:
            json_resp = json.loads(texto) if texto else {}
            respuesta = json_resp.get("codigo") or f"comprobante {json_resp.get('codigo_operacion', '')}".strip()
        except (ValueError, AttributeError):
            respuesta = texto[:60]
        casos.append({
            "numero": numero, "validacion": validacion, "metodo": entrada["request"]["method"],
            "cuerpo": entrada["request"].get("postData", {}).get("text", "") or "—",
            "estado": estado, "respuesta": respuesta,
            "correcto": estado < 500 and estado in VALIDACIONES[validacion][1],
        })
    return casos


def resumen(casos: list[dict]) -> list[dict]:
    """Una fila por validación: cuántos casos, cuáles filas y si todos fueron correctos."""
    filas = []
    for nombre, (descripcion, _) in VALIDACIONES.items():
        del_grupo = [c for c in casos if c["validacion"] == nombre]
        filas.append({"validacion": nombre, "descripcion": descripcion, "casos": len(del_grupo),
                      "filas": [c["numero"] for c in del_grupo],
                      "correcto": all(c["correcto"] for c in del_grupo) if del_grupo else None})
    return filas


_CSS = """:root{--bg:#F5F7FA;--sf:#fff;--fg:#17212F;--mu:#566477;--ln:#D8DFE8;--ac:#1F5FBF;--acs:#E3ECFA;--ok:#1F7A55;--wa:#B4520C}
@media (prefers-color-scheme:dark){:root{--bg:#0F1621;--sf:#172231;--fg:#E6ECF4;--mu:#9AA9BC;--ln:#2A394D;--ac:#7FB0F5;--acs:#1C2F4A;--ok:#6FD3A6;--wa:#F2A36B;color-scheme:dark}}
body{background:var(--bg);color:var(--fg);font:16px/1.55 Verdana,sans-serif;margin:0}
.w{max-width:1000px;margin:0 auto;padding:32px 18px 60px;display:flex;flex-direction:column;gap:24px}
h1{font-size:28px;margin:0}h2{font-size:21px;margin:0}p{margin:0}.mu{color:var(--mu)}
.kpis{display:flex;flex-wrap:wrap;gap:12px}.k{flex:1;min-width:150px;background:var(--sf);border:1px solid var(--ln);border-radius:12px;padding:14px 16px}.k b{display:block;font-size:32px}
.tb{overflow-x:auto;background:var(--sf);border:1px solid var(--ln);border-radius:12px}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:8px 12px;border-bottom:1px solid var(--ln);text-align:left;vertical-align:top}th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--mu)}
code{font-family:Consolas,monospace;font-size:13px}.ok{color:var(--ok);font-weight:bold}.wa{color:var(--wa);font-weight:bold}
.pill{background:var(--acs);color:var(--ac);border-radius:99px;padding:2px 9px;font-size:12px;white-space:nowrap}"""


def generar_html(casos: list[dict], operacion: str, semilla: str, observaciones: list[str], fecha: str) -> str:
    e = html.escape
    n500 = sum(1 for c in casos if c["estado"] >= 500)
    partes = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
              f"<title>Schemathesis · {e(operacion)}</title><style>{_CSS}</style><div class=w>",
              f"<div><p class=mu>Pruebas técnicas generadas desde el contrato OpenAPI · ejecución {e(fecha)} · modo {e(semilla)}</p>"
              f"<h1>Schemathesis · {e(operacion)}</h1></div>",
              f"<div class=kpis><div class=k><b>{len(casos)}</b>casos generados</div>"
              f"<div class=k><b class={'wa' if n500 else 'ok'}>{n500}</b>errores 500</div>"
              f"<div class=k><b>{len(observaciones)}</b>observaciones de Schemathesis</div></div>"]
    if observaciones:
        partes.append("<p>Observaciones: " + " · ".join(e(o) for o in observaciones) + "</p>")
    partes.append("<h2>Dónde está cada validación de entrada</h2><div class=tb><table><tr><th>Validación</th>"
                  "<th>Qué se envió y qué se espera</th><th>Casos</th><th>Filas</th><th>¿Correcto?</th></tr>")
    for fila in resumen(casos):
        estado = ("<td class=wa>No generado</td>" if fila["correcto"] is None
                  else f"<td class={'ok' if fila['correcto'] else 'wa'}>{'Sí' if fila['correcto'] else 'NO'}</td>")
        lista = ", ".join(f"#{n}" for n in fila["filas"]) or "—"
        partes.append(f"<tr><td><b>{e(fila['validacion'])}</b></td><td>{e(fila['descripcion'])}</td>"
                      f"<td>{fila['casos']}</td><td>{lista}</td>{estado}</tr>")
    partes.append("</table></div><h2>Todos los casos</h2><div class=tb><table><tr><th>#</th><th>Validación</th>"
                  "<th>Método</th><th>Cuerpo enviado</th><th>Estado</th><th>Respuesta</th></tr>")
    for c in casos:
        partes.append(f"<tr><td>{c['numero']}</td><td><span class=pill>{e(c['validacion'])}</span></td><td>{c['metodo']}</td>"
                      f"<td><code>{e(c['cuerpo'][:110])}</code></td><td class={'ok' if c['correcto'] else 'wa'}>{c['estado']}</td>"
                      f"<td><code>{e(str(c['respuesta']))}</code></td></tr>")
    partes.append("</table></div></div>")
    return "".join(partes)
