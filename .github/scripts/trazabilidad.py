"""QUÉ ES: genera la MATRIZ DE TRAZABILIDAD del módulo G2 (pago de servicios).

PARA QUÉ:
  Responde a la pregunta "¿qué parte de la especificación está probada y cómo le fue?".
  Une los resultados de ESTE run (pytest para la API y Robot Framework para la web) y arma
  una tabla: Historia de usuario (HU) → caso de prueba → nivel (api / contrato / web)
  → resultado → defecto conocido (DEF-0X, enlazado a docs/defectos.md).
  Arriba pone un resumen por HU y la cobertura de la especificación (las 7 HU del módulo:
  cuáles tienen casos en este run y cuáles quedan "fuera de alcance").
  Genera dos versiones:
    - Markdown (.md): para docs/trazabilidad.md y para el resumen del run en GitHub.
    - HTML (.html): página bonita y autocontenida para GitHub Pages (modo claro y oscuro).

CÓMO SE USA (desde la raíz del repo):
  python .github/scripts/trazabilidad.py --api reportes/api/junit.xml --web reportes/web/output.xml \
      --salida-md docs/trazabilidad.md --salida-html sitio/trazabilidad.html [--summary]
  --summary  además agrega la matriz al resumen del run (variable GITHUB_STEP_SUMMARY).
  Si falta alguno de los XML (p. ej. solo se corrió la API), ese nivel sale "no ejecutado".

  Solo usa la librería estándar de Python. Los otros dos scripts (resumen.py y portada.py)
  reutilizan las funciones de lectura y el estilo visual definidos aquí.
"""
import argparse
import html
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
DEFECTOS_MD = RAIZ_REPO / "docs" / "defectos.md"

# Lo que dice la especificación del módulo G2 (docs/requisitos.md).
HU_ESPECIFICACION = [
    ("HU-G2-01", "Consultar deudas"),
    ("HU-G2-02", "Pagar una deuda"),
    ("HU-G2-03", "Afiliar un servicio"),
    ("HU-G2-04", "Ver servicios afiliados"),
    ("HU-G2-05", "Editar afiliación y débito automático"),
    ("HU-G2-06", "Desafiliar"),
    ("HU-G2-07", "Ver pagos y comprobantes"),
]
SIN_HU = "(sin HU)"
NIVELES = ["api", "contrato", "web"]

# Los 4 resultados posibles de un caso, con su ícono y texto para el público.
ICONO = {"passed": "✅", "xfailed": "⚠️", "failed": "❌", "skipped": "⏭️"}
TEXTO = {"passed": "Pasa", "xfailed": "Fallo esperado (defecto conocido)", "failed": "Falla", "skipped": "Omitida"}


# ---------------------------------------------------------------------------------------
# 1. Lectura de resultados
# ---------------------------------------------------------------------------------------
def _caso(nivel, nombre, etiquetas, estado, defecto="", mensaje="", cp=""):
    """Un caso de prueba ya normalizado (igual para API y web)."""
    return {
        "nivel": nivel,
        "nombre": nombre,
        "cp": cp,
        "etiquetas": etiquetas,
        "hu": sorted({e for e in etiquetas if e.startswith("HU-")}) or [SIN_HU],
        "ca": sorted({e for e in etiquetas if e.startswith("CA")}),
        "estado": estado,
        "defecto": defecto,
        "mensaje": mensaje,
    }


def _primera_linea(texto, largo=160):
    texto = (texto or "").strip().splitlines()
    return texto[0][:largo] if texto else ""


def nombre_legible(nombre):
    """test_pagar_deuda_con_mora[ELECTRO] → 'pagar deuda con mora [ELECTRO]'."""
    nombre = nombre.removeprefix("test_")
    base, corchete, resto = nombre.partition("[")
    return base.replace("_", " ").strip() + (f" [{resto}" if corchete else "")


def leer_junit(ruta):
    """Lee el JUnit XML de pytest. Devuelve la lista de casos."""
    casos = []
    for tc in ET.parse(ruta).getroot().iter("testcase"):
        props = {p.get("name"): p.get("value", "") for p in tc.iter("property")}
        etiquetas = [e.strip() for e in props.get("etiquetas", "").split(",") if e.strip()]
        defecto = props.get("defecto", "")
        falla = tc.find("failure")
        if falla is None:
            falla = tc.find("error")
        omitida = tc.find("skipped")
        if falla is not None:
            estado, mensaje = "failed", falla.get("message") or falla.text
        elif omitida is not None and omitida.get("type") == "pytest.xfail":
            estado, mensaje = "xfailed", omitida.get("message", "")
            if not defecto:  # si no vino la propiedad, se busca "DEF-0X" en el mensaje
                encontrado = re.search(r"DEF-\d+", mensaje)
                defecto = encontrado.group(0) if encontrado else ""
        elif omitida is not None:
            estado, mensaje = "skipped", omitida.get("message") or omitida.text
        else:
            estado, mensaje = "passed", ""
        nivel = "contrato" if "schemathesis" in etiquetas else "api"
        casos.append(_caso(nivel, nombre_legible(tc.get("name", "")), etiquetas, estado,
                           defecto, _primera_linea(mensaje)))
    return casos


def leer_robot(ruta):
    """Lee el output.xml de Robot Framework (las pruebas pueden estar en suites anidadas)."""
    casos = []
    for test in ET.parse(ruta).getroot().iter("test"):
        # Solo las etiquetas propias de la prueba (no las de las keywords de adentro).
        etiquetas = [t.text.strip() for t in test.findall("tag") + test.findall("tags/tag") if t.text]
        status = test.find("status")
        robot = (status.get("status") if status is not None else "FAIL").upper()
        defecto = next((e for e in etiquetas if re.fullmatch(r"DEF-\d+", e)), "")
        if robot == "PASS":
            estado = "passed"
        elif robot == "SKIP":
            estado = "skipped"
        else:  # FAIL: si la prueba tiene la etiqueta de un defecto conocido, es fallo esperado
            estado = "xfailed" if defecto else "failed"
        cp = next((e for e in etiquetas if e.upper().startswith("CP-")), "")
        mensaje = status.text if status is not None and estado != "passed" else ""
        casos.append(_caso("web", test.get("name", ""), etiquetas, estado, defecto,
                           _primera_linea(mensaje), cp))
    return casos


def leer_reporte(ruta):
    """Detecta el formato y lee. Devuelve (tipo, casos) o (None, None) si no existe o no se puede leer."""
    if not ruta or not Path(ruta).is_file():
        return None, None
    try:
        raiz = ET.parse(ruta).getroot()
    except ET.ParseError as error:
        print(f"Aviso: no se pudo leer {ruta}: {error}", file=sys.stderr)
        return None, None
    if raiz.tag == "robot":
        return "robot", leer_robot(ruta)
    if raiz.tag in ("testsuites", "testsuite"):
        return "junit", leer_junit(ruta)
    print(f"Aviso: {ruta} no parece JUnit ni Robot (raíz <{raiz.tag}>)", file=sys.stderr)
    return None, None


def contar(casos):
    total = defaultdict(int)
    for c in casos:
        total[c["estado"]] += 1
    return total


# ---------------------------------------------------------------------------------------
# 2. Datos del run (variables que GitHub Actions pone en el entorno)
# ---------------------------------------------------------------------------------------
def _repo_por_git():
    try:
        url = subprocess.run(["git", "-C", str(RAIZ_REPO), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    encontrado = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    return encontrado.group(1) if encontrado else ""


def contexto_run():
    env = os.environ.get
    servidor = env("GITHUB_SERVER_URL", "https://github.com")
    repo = env("GITHUB_REPOSITORY") or _repo_por_git() or "usuario/qolqe-wallet-services"
    run_id = env("GITHUB_RUN_ID", "")
    lima = datetime.now(timezone(timedelta(hours=-5)))
    return {
        "numero": env("GITHUB_RUN_NUMBER", "local"),
        "commit": (env("GITHUB_SHA") or "local")[:7],
        "rama": env("GITHUB_REF_NAME", "local"),
        "repo": repo,
        "url_repo": f"{servidor}/{repo}",
        "url_run": f"{servidor}/{repo}/actions/runs/{run_id}" if run_id else "",
        "url_commit": f"{servidor}/{repo}/commit/{env('GITHUB_SHA')}" if env("GITHUB_SHA") else "",
        "fecha": lima.strftime("%d/%m/%Y %H:%M") + " (hora de Lima)",
        "url_defectos": f"{servidor}/{repo}/blob/main/docs/defectos.md",
    }


# ---------------------------------------------------------------------------------------
# 3. Enlaces a los defectos (con el ancla del título dentro de docs/defectos.md)
# ---------------------------------------------------------------------------------------
def _anclas_defectos():
    """{'DEF-01': 'def-01-se-acepta-...'} leyendo los títulos '## DEF-0X: ...' (como los arma GitHub)."""
    anclas = {}
    if DEFECTOS_MD.is_file():
        for linea in DEFECTOS_MD.read_text(encoding="utf-8").splitlines():
            encontrado = re.match(r"##\s+(DEF-\d+)\b.*", linea)
            if encontrado:
                titulo = linea.lstrip("#").strip().lower()
                anclas[encontrado.group(1)] = re.sub(r"[^\w\- ]", "", titulo).replace(" ", "-")
    return anclas


ANCLAS = _anclas_defectos()


def url_defecto(defecto, base):
    ancla = ANCLAS.get(defecto)
    return f"{base}#{ancla}" if ancla else base


# ---------------------------------------------------------------------------------------
# 4. Armado de la matriz
# ---------------------------------------------------------------------------------------
def filas_matriz(casos):
    """Una fila por (HU, caso). Si un caso cubre 2 HU, aparece en las dos."""
    filas = []
    for c in casos:
        for hu in c["hu"]:
            filas.append({**c, "hu_fila": hu})
    orden_nivel = {n: i for i, n in enumerate(NIVELES)}
    filas.sort(key=lambda f: (f["hu_fila"] == SIN_HU, f["hu_fila"], orden_nivel[f["nivel"]], f["cp"], f["nombre"]))
    return filas


def resumen_por_hu(filas):
    por_hu = {}
    for f in filas:
        d = por_hu.setdefault(f["hu_fila"], {"casos": 0, "niveles": defaultdict(int), "estados": defaultdict(int),
                                             "defectos": set()})
        d["casos"] += 1
        d["niveles"][f["nivel"]] += 1
        d["estados"][f["estado"]] += 1
        if f["defecto"] and f["estado"] == "xfailed":
            d["defectos"].add(f["defecto"])
    return dict(sorted(por_hu.items(), key=lambda x: (x[0] == SIN_HU, x[0])))


def estado_global(d):
    if d["estados"]["failed"]:
        return "❌", "Hay fallos nuevos"
    if d["estados"]["passed"] + d["estados"]["xfailed"] == 0:
        return "⏭️", "Solo omitidas"
    if d["estados"]["xfailed"]:
        return "✅", "OK (con defectos conocidos)"
    return "✅", "OK"


def nombre_caso(f):
    return f"{f['cp']} · {f['nombre']}" if f["cp"] else f["nombre"]


def texto_cobertura(d):
    return " · ".join(f"{n} {d['niveles'][n]}" for n in NIVELES if d["niveles"][n]) or "—"


# ---------------------------------------------------------------------------------------
# 5. Salida Markdown
# ---------------------------------------------------------------------------------------
def _md(texto):
    """Escapa lo que rompe una tabla Markdown."""
    return str(texto).replace("|", "\\|").replace("\n", " ")


def resultado_md(f, base_defectos):
    if f["estado"] == "xfailed":
        defecto = f["defecto"] or "defecto sin ID"
        enlace = f"[{defecto}]({url_defecto(defecto, base_defectos)})" if f["defecto"] else defecto
        return f"⚠️ xfailed → {enlace}"
    return f"{ICONO[f['estado']]} {f['estado']}"


def generar_md(casos_api, casos_web, ctx, base_defectos):
    casos = (casos_api or []) + (casos_web or [])
    filas = filas_matriz(casos)
    por_hu = resumen_por_hu(filas)
    run = f"[#{ctx['numero']}]({ctx['url_run']})" if ctx["url_run"] else f"#{ctx['numero']}"
    commit = f"[`{ctx['commit']}`]({ctx['url_commit']})" if ctx["url_commit"] else f"`{ctx['commit']}`"
    total = contar(casos)
    out = [
        "<!-- QUÉ ES: matriz de trazabilidad generada automáticamente por .github/scripts/trazabilidad.py.",
        "     No editar a mano: se vuelve a generar en cada ejecución del pipeline. -->",
        "",
        "# Matriz de trazabilidad · G2 Pago de servicios",
        "",
        f"Run {run} · commit {commit} · rama `{ctx['rama']}` · {ctx['fecha']}",
        "",
        "Cada fila une una **historia de usuario (HU)** con el **caso de prueba** que la verifica, "
        "el **nivel** donde se prueba y el **resultado de esta ejecución**.",
        "",
        f"**Totales:** ✅ {total['passed']} pasan · ⚠️ {total['xfailed']} fallos esperados (defectos conocidos) · "
        f"❌ {total['failed']} fallan · ⏭️ {total['skipped']} omitidas",
        "",
        "Fuentes: API " + ("✔️ ejecutada" if casos_api is not None else "— no ejecutada")
        + " · Web " + ("✔️ ejecutada" if casos_web is not None else "— no ejecutada"),
        "",
        "## Cobertura de la especificación",
        "",
        "| HU | Descripción | ¿Tiene casos en este run? | Casos |",
        "|---|---|---|---:|",
    ]
    for hu, titulo in HU_ESPECIFICACION:
        n = por_hu[hu]["casos"] if hu in por_hu else 0
        out.append(f"| {hu} | {titulo} | {'✅ Sí' if n else '➖ Fuera de alcance'} | {n} |")
    cubiertas = sum(1 for hu, _ in HU_ESPECIFICACION if hu in por_hu)
    out += ["", f"**{cubiertas} de {len(HU_ESPECIFICACION)} HU** del módulo tienen casos en este run.", ""]

    out += ["## Resumen por HU", ""]
    if por_hu:
        out += ["| HU | Casos | Cobertura por nivel | ✅ | ⚠️ | ❌ | ⏭️ | Defectos | Estado |",
                "|---|---:|---|---:|---:|---:|---:|---|---|"]
        for hu, d in por_hu.items():
            icono, texto = estado_global(d)
            defectos = ", ".join(f"[{x}]({url_defecto(x, base_defectos)})" for x in sorted(d["defectos"])) or "—"
            e = d["estados"]
            out.append(f"| {hu} | {d['casos']} | {texto_cobertura(d)} | {e['passed']} | {e['xfailed']} | "
                       f"{e['failed']} | {e['skipped']} | {defectos} | {icono} {texto} |")
    else:
        out.append("_No hay resultados: no se ejecutó ninguna prueba._")
    out += ["", "## Matriz HU → caso → nivel → resultado", ""]
    if filas:
        out += ["| HU | Caso de prueba | CA | Nivel | Resultado |", "|---|---|---|---|---|"]
        for f in filas:
            out.append(f"| {f['hu_fila']} | {_md(nombre_caso(f))} | {', '.join(f['ca']) or '—'} | {f['nivel']} | "
                       f"{resultado_md(f, base_defectos)} |")
    else:
        out.append("_Sin casos._")
    out += ["", "Leyenda: ✅ pasa · ⚠️ fallo esperado: la prueba detecta un defecto ya reportado en "
            f"[defectos.md]({base_defectos}) · ❌ falla (fallo nuevo, hay que analizarlo) · ⏭️ omitida.", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------------------
# 6. Salida HTML (autocontenida; portada.py reutiliza CSS y encabezado)
# ---------------------------------------------------------------------------------------
CSS = """
:root{--fondo:#f5f7fb;--tarjeta:#fff;--texto:#1d2433;--suave:#5b6577;--borde:#e3e7ef;--marca:#4f46e5;
--ok:#e8f7ee;--ok-t:#146c3a;--av:#fff6d6;--av-t:#7a5a00;--mal:#fde8e8;--mal-t:#a11d1d;--om:#eef0f4;--om-t:#4b5363}
@media (prefers-color-scheme:dark){:root{--fondo:#0f141c;--tarjeta:#171e29;--texto:#e6eaf2;--suave:#9aa4b5;
--borde:#2a3342;--marca:#8b85ff;--ok:#12301f;--ok-t:#7fdba3;--av:#3a3110;--av-t:#f3d36b;--mal:#3d1717;
--mal-t:#ff9b9b;--om:#232b38;--om-t:#b6bfcc}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--texto);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
a{color:var(--marca)}
header.portada{background:linear-gradient(135deg,#4f46e5,#0ea5e9);color:#fff;border-radius:16px;padding:24px;margin-bottom:24px}
header.portada h1{margin:0 0 4px;font-size:1.6rem;line-height:1.25}
header.portada p{margin:0;opacity:.92}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.meta span,.meta a{background:rgba(255,255,255,.18);color:#fff;border-radius:999px;padding:3px 12px;font-size:.88rem;text-decoration:none}
.meta a:hover{background:rgba(255,255,255,.3)}
h2{font-size:1.2rem;margin:32px 0 6px}
p.ayuda{color:var(--suave);margin:0 0 12px}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tarjeta{background:var(--tarjeta);border:1px solid var(--borde);border-radius:12px;padding:14px 16px}
.tarjeta b{display:block;font-size:1.8rem;line-height:1.1}
.tarjeta span{color:var(--suave);font-size:.9rem}
.tabla{overflow-x:auto;background:var(--tarjeta);border:1px solid var(--borde);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:.93rem}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--borde);vertical-align:top}
th{font-size:.8rem;text-transform:uppercase;letter-spacing:.03em;color:var(--suave);background:var(--tarjeta);position:sticky;top:0}
tr:last-child td{border-bottom:0}
td:first-child{white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.passed td{background:var(--ok)} tr.xfailed td{background:var(--av)} tr.failed td{background:var(--mal)} tr.skipped td{background:var(--om)}
.chip{display:inline-block;border-radius:999px;padding:1px 10px;font-size:.82rem;font-weight:600;white-space:nowrap}
.chip.passed{background:var(--ok);color:var(--ok-t)} .chip.xfailed{background:var(--av);color:var(--av-t)}
.chip.failed{background:var(--mal);color:var(--mal-t)} .chip.skipped{background:var(--om);color:var(--om-t)}
.nivel{display:inline-block;border:1px solid var(--borde);border-radius:6px;padding:0 7px;font-size:.8rem;margin:1px 2px 1px 0;white-space:nowrap}
.detalle{color:var(--suave);font-size:.82rem;display:block;margin-top:2px;word-break:break-word}
.leyenda{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0;color:var(--suave);font-size:.88rem}
footer{color:var(--suave);font-size:.85rem;margin-top:32px;text-align:center}
@media (max-width:600px){header.portada h1{font-size:1.3rem}th,td{padding:8px}}
"""


def esc(texto):
    return html.escape(str(texto))


def pagina_html(titulo, subtitulo, ctx, cuerpo):
    """Plantilla común: encabezado con datos del run + cuerpo + pie."""
    meta = [f"<span>Run #{esc(ctx['numero'])}</span>",
            (f"<a href='{esc(ctx['url_commit'])}'>Commit {esc(ctx['commit'])}</a>" if ctx["url_commit"]
             else f"<span>Commit {esc(ctx['commit'])}</span>"),
            f"<span>Rama {esc(ctx['rama'])}</span>", f"<span>{esc(ctx['fecha'])}</span>"]
    if ctx["url_run"]:
        meta.append(f"<a href='{esc(ctx['url_run'])}'>Ver el run en GitHub Actions ↗</a>")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(titulo)}</title><style>{CSS}</style></head>
<body><main>
<header class="portada"><h1>{esc(titulo)}</h1><p>{esc(subtitulo)}</p>
<div class="meta">{''.join(meta)}</div></header>
{cuerpo}
<footer>Generado automáticamente por el pipeline de GitHub Actions ·
<a href="{esc(ctx['url_repo'])}">{esc(ctx['repo'])}</a></footer>
</main></body></html>
"""


def _chip(estado, defecto="", base=""):
    if estado == "xfailed":
        enlace = (f" → <a href='{esc(url_defecto(defecto, base))}'>{esc(defecto)}</a>" if defecto else "")
        return f"<span class='chip xfailed'>⚠️ Fallo esperado{enlace}</span>"
    return f"<span class='chip {estado}'>{ICONO[estado]} {TEXTO[estado]}</span>"


def generar_html(casos_api, casos_web, ctx):
    base = ctx["url_defectos"]
    casos = (casos_api or []) + (casos_web or [])
    filas = filas_matriz(casos)
    por_hu = resumen_por_hu(filas)
    total = contar(casos)
    partes = []

    tarjetas = [(total["passed"], "✅ Pasan"), (total["xfailed"], "⚠️ Fallos esperados (defectos conocidos)"),
                (total["failed"], "❌ Fallan"), (total["skipped"], "⏭️ Omitidas")]
    fuentes = ("API: " + ("ejecutada" if casos_api is not None else "no ejecutada") + " · Web: "
               + ("ejecutada" if casos_web is not None else "no ejecutada"))
    partes.append(f"<h2>Resultado de esta ejecución</h2><p class='ayuda'>{len(casos)} casos de prueba · {fuentes}</p>"
                  "<div class='tarjetas'>" + "".join(f"<div class='tarjeta'><b>{n}</b><span>{esc(t)}</span></div>"
                                                     for n, t in tarjetas) + "</div>")

    cubiertas = sum(1 for hu, _ in HU_ESPECIFICACION if hu in por_hu)
    filas_spec = []
    for hu, titulo in HU_ESPECIFICACION:
        n = por_hu[hu]["casos"] if hu in por_hu else 0
        estado = (f"<span class='chip passed'>✅ Con casos</span>" if n
                  else "<span class='chip skipped'>➖ Fuera de alcance</span>")
        filas_spec.append(f"<tr><td><b>{hu}</b></td><td>{esc(titulo)}</td><td>{estado}</td><td class='num'>{n}</td></tr>")
    partes.append("<h2>Cobertura de la especificación</h2>"
                  f"<p class='ayuda'>El módulo G2 tiene {len(HU_ESPECIFICACION)} historias de usuario; "
                  f"<b>{cubiertas}</b> tienen pruebas en este run.</p>"
                  "<div class='tabla'><table><thead><tr><th>HU</th><th>Qué pide</th><th>Estado</th><th>Casos</th>"
                  "</tr></thead><tbody>" + "".join(filas_spec) + "</tbody></table></div>")

    if por_hu:
        filas_hu = []
        for hu, d in por_hu.items():
            icono, texto = estado_global(d)
            clase = "failed" if icono == "❌" else ("skipped" if icono == "⏭️" else "passed")
            niveles = "".join(f"<span class='nivel'>{n} {d['niveles'][n]}</span>" for n in NIVELES if d["niveles"][n])
            defectos = ", ".join(f"<a href='{esc(url_defecto(x, base))}'>{esc(x)}</a>" for x in sorted(d["defectos"])) or "—"
            e = d["estados"]
            filas_hu.append(f"<tr><td><b>{esc(hu)}</b></td><td class='num'>{d['casos']}</td><td>{niveles}</td>"
                            f"<td class='num'>{e['passed']}</td><td class='num'>{e['xfailed']}</td>"
                            f"<td class='num'>{e['failed']}</td><td class='num'>{e['skipped']}</td><td>{defectos}</td>"
                            f"<td><span class='chip {clase}'>{icono} {esc(texto)}</span></td></tr>")
        partes.append("<h2>Resumen por historia de usuario</h2><p class='ayuda'>Una HU está ✅ si todas sus pruebas "
                      "pasan o fallan solo por defectos ya reportados; ❌ si aparece un fallo nuevo.</p>"
                      "<div class='tabla'><table><thead><tr><th>HU</th><th>Casos</th><th>Cobertura por nivel</th>"
                      "<th>✅</th><th>⚠️</th><th>❌</th><th>⏭️</th><th>Defectos</th><th>Estado</th></tr></thead><tbody>"
                      + "".join(filas_hu) + "</tbody></table></div>")

    if filas:
        filas_m = []
        for f in filas:
            detalle = (f"<span class='detalle'>{esc(f['mensaje'])}</span>"
                       if f["mensaje"] and f["estado"] in ("failed", "skipped") else "")
            cp = f"<b>{esc(f['cp'])}</b> · " if f["cp"] else ""
            filas_m.append(f"<tr class='{f['estado']}'><td><b>{esc(f['hu_fila'])}</b></td>"
                           f"<td>{cp}{esc(f['nombre'])}{detalle}</td><td>{esc(', '.join(f['ca']) or '—')}</td>"
                           f"<td><span class='nivel'>{esc(f['nivel'])}</span></td>"
                           f"<td>{_chip(f['estado'], f['defecto'], base)}</td></tr>")
        partes.append("<h2>Matriz de trazabilidad</h2><p class='ayuda'>Historia de usuario → caso de prueba → "
                      "nivel donde se prueba → resultado de esta ejecución.</p>"
                      "<div class='tabla'><table><thead><tr><th>HU</th><th>Caso de prueba</th><th>CA</th>"
                      "<th>Nivel</th><th>Resultado</th></tr></thead><tbody>" + "".join(filas_m) + "</tbody></table></div>")
    else:
        partes.append("<h2>Matriz de trazabilidad</h2><p class='ayuda'>No hay resultados: no se ejecutó ninguna prueba.</p>")

    partes.append("<div class='leyenda'>"
                  "<span class='chip passed'>✅ Pasa</span>"
                  f"<span class='chip xfailed'>⚠️ Fallo esperado: detecta un defecto ya reportado en "
                  f"<a href='{esc(base)}'>defectos.md</a></span>"
                  "<span class='chip failed'>❌ Falla: fallo nuevo, hay que analizarlo</span>"
                  "<span class='chip skipped'>⏭️ Omitida</span></div>"
                  "<p class='ayuda' style='margin-top:10px'>Niveles: <b>api</b> = reglas de negocio probadas "
                  "directo contra el servidor · <b>contrato</b> = pruebas generadas automáticamente desde la "
                  "especificación OpenAPI (Schemathesis) · <b>web</b> = un robot usa la app en el navegador.</p>")
    return pagina_html("Matriz de trazabilidad · G2 Pago de servicios",
                       "Qué historias de usuario están probadas y cómo le fue a cada prueba en esta ejecución.",
                       ctx, "\n".join(partes))


def agregar_a_summary(texto):
    """Agrega Markdown al resumen del run de GitHub; si no estamos en GitHub, lo imprime."""
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
    else:
        sys.stdout.write(texto + "\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Genera la matriz de trazabilidad HU → caso → nivel → resultado.")
    p.add_argument("--api", help="JUnit XML de pytest (p. ej. reportes/api/junit.xml)")
    p.add_argument("--web", help="output.xml de Robot Framework (p. ej. reportes/web/output.xml)")
    p.add_argument("--salida-md", help="archivo Markdown a generar (p. ej. docs/trazabilidad.md)")
    p.add_argument("--salida-html", help="archivo HTML a generar (p. ej. sitio/trazabilidad.html)")
    p.add_argument("--summary", action="store_true", help="agrega la matriz al resumen del run de GitHub")
    args = p.parse_args()

    _, casos_api = leer_reporte(args.api)
    _, casos_web = leer_reporte(args.web)
    ctx = contexto_run()

    if args.salida_md:
        salida = Path(args.salida_md)
        salida.parent.mkdir(parents=True, exist_ok=True)
        # Dentro del repo el enlace a defectos.md es relativo (funciona en GitHub y en local);
        # fuera del repo se usa el enlace completo de GitHub.
        if salida.resolve().is_relative_to(RAIZ_REPO):
            base = Path(os.path.relpath(DEFECTOS_MD, salida.resolve().parent)).as_posix()
        else:
            base = ctx["url_defectos"]
        salida.write_text(generar_md(casos_api, casos_web, ctx, base), encoding="utf-8")
        print(f"Matriz Markdown: {salida}")
    if args.salida_html:
        salida = Path(args.salida_html)
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(generar_html(casos_api, casos_web, ctx), encoding="utf-8")
        print(f"Matriz HTML: {salida}")
    if args.summary:
        # En el resumen del run los enlaces relativos no funcionan: se usa el enlace completo.
        agregar_a_summary(generar_md(casos_api, casos_web, ctx, ctx["url_defectos"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
