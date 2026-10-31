"""QUÉ ES: configuración común que pytest carga ANTES de cualquier prueba.

PARA QUÉ:
  1. Hace que las pruebas usen su propia base de datos (datos/pruebas.db), así no borran
     ni modifican los datos de la app que usas en la demo (datos/qolqe.db). También activa
     el modo prueba, que habilita la API de soporte (/api/pruebas/*).
  2. Al terminar cada ejecución imprime en la terminal el RESUMEN AUTOMÁTICO:
     - Funcional (los .feature): casos por HU y por técnica, y cada fallo con su defecto.
     - Técnico (Schemathesis): casos generados por validación de entrada.
     Los números salen de ESA ejecución: si el código cambia, el resumen cambia.
"""
import os
from collections import defaultdict

os.environ.setdefault("QOLQE_BD", "datos/pruebas.db")
os.environ.setdefault("QOLQE_MODO_PRUEBA", "1")

# Fallos ya analizados y reportados en docs/defectos.md: fragmento del nombre de la prueba → defecto.
# Un fallo que no esté aquí sale como "NUEVO": hay que analizarlo (posible regresión o defecto nuevo).
DEFECTOS_CONOCIDOS = [
    ("13 digitos", "DEF-01"),
    ("[60-PENDIENTE]", "DEF-03"),
    ("60 dias, aun se puede pagar", "DEF-03"),
    ("conteo_de_días_de_atraso", "DEF-02"),
    ("mora_de_05__diario", "DEF-02"),
    ("ya_vencidas_antes_de_activar", "DEF-04"),
]
TECNICAS = ["camino-feliz", "particion", "valor-limite", "efecto", "concurrencia", "seguridad", "tecnico", "contrato", "schemathesis"]

_etiquetas: dict[str, set[str]] = {}
_resultados: dict[str, dict] = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "schemathesis: prueba técnica generada con Schemathesis desde el contrato OpenAPI")


def pytest_collection_modifyitems(items):
    for item in items:
        _etiquetas[item.nodeid] = {m.name for m in item.iter_markers()}


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        mensaje = ""
        if report.failed and hasattr(report.longrepr, "reprcrash"):
            mensaje = report.longrepr.reprcrash.message.splitlines()[0]
        _resultados[report.nodeid] = {"estado": report.outcome, "mensaje": mensaje}


def _defecto(nodeid: str) -> str:
    return next((d for fragmento, d in DEFECTOS_CONOCIDOS if fragmento in nodeid), "NUEVO, analizar")


def _nombre(nodeid: str) -> str:
    return nodeid.split("::")[-1].removeprefix("test_").replace("_", " ")


def _resumen_funcional(tr):
    funcionales = {n: r for n, r in _resultados.items() if "schemathesis" not in _etiquetas.get(n, set())}
    if not funcionales:
        return
    tr.write_sep("=", "RESUMEN FUNCIONAL · pytest-bdd · features/*.feature")
    por_hu = defaultdict(lambda: [0, 0])
    por_tecnica = defaultdict(lambda: [0, 0])
    for nodeid, r in funcionales.items():
        etiquetas = _etiquetas.get(nodeid, set())
        hu = sorted(e for e in etiquetas if e.startswith("HU-")) or ["(sin HU: humo)"]
        indice = 0 if r["estado"] == "passed" else 1
        por_hu[hu[0]][indice] += 1
        for tecnica in TECNICAS:
            if tecnica in etiquetas:
                por_tecnica[tecnica][indice] += 1
    tr.write_line(f"  {'Historia de usuario':<22}{'Casos':>7}{'Pasan':>7}{'Fallan':>8}")
    for hu in sorted(por_hu):
        ok, ko = por_hu[hu]
        tr.write_line(f"  {hu:<22}{ok + ko:>7}{ok:>7}{ko:>8}")
    total_ok = sum(v[0] for v in por_hu.values())
    total_ko = sum(v[1] for v in por_hu.values())
    tr.write_line(f"  {'TOTAL':<22}{total_ok + total_ko:>7}{total_ok:>7}{total_ko:>8}")
    tr.write_line("")
    tr.write_line("  Por técnica: " + " · ".join(
        f"{t} {v[0]}/{v[0] + v[1]}" for t, v in ((t, por_tecnica[t]) for t in TECNICAS) if sum(v)))
    fallos = [(n, r) for n, r in funcionales.items() if r["estado"] != "passed"]
    if fallos:
        tr.write_line("")
        tr.write_line("  Fallos (cada uno evidencia un defecto):")
        for nodeid, r in sorted(fallos, key=lambda x: _defecto(x[0])):
            tr.write_line(f"   [{_defecto(nodeid)}] {_nombre(nodeid)[:95]}")
            if r["mensaje"]:
                tr.write_line(f"            {r['mensaje'][:110]}")
        nuevos = sum(1 for n, _ in fallos if _defecto(n).startswith("NUEVO"))
        defectos = sorted({_defecto(n) for n, _ in fallos} - {"NUEVO, analizar"})
        tr.write_line("")
        tr.write_line(f"  {len(fallos)} fallos → defectos conocidos: {', '.join(defectos) or 'ninguno'}"
                      + (f" · {nuevos} fallo(s) NUEVO(S) por analizar" if nuevos else " · sin fallos nuevos"))
    tr.write_line("  Reporte HTML: pytest --html=reportes/pytest/reporte.html --self-contained-html")


def _resumen_tecnico(tr, config):
    datos = getattr(config, "resumen_tecnico", None)
    if datos is None:
        return
    casos = datos["casos"]
    tr.write_sep("=", f"RESUMEN TÉCNICO · Schemathesis · {datos['operacion']}")
    tr.write_line(f"  {len(casos)} casos generados desde el contrato OpenAPI · errores 500: "
                  f"{sum(1 for c in casos if c['estado'] >= 500)} · modo {datos['semilla']}")
    tr.write_line("")
    tr.write_line(f"  {'Validación de entrada':<36}{'Casos':>6}  {'¿Correcto?':<12}Filas en el reporte")
    for f in datos["filas"]:
        estado = "No generado" if f["correcto"] is None else ("Sí" if f["correcto"] else "NO")
        filas = ", ".join(f"#{n}" for n in f["filas"][:12]) + (" …" if len(f["filas"]) > 12 else "")
        tr.write_line(f"  {f['validacion']:<36}{f['casos']:>6}  {estado:<12}{filas}")
    if datos["observaciones"]:
        tr.write_line("")
        tr.write_line("  Observaciones de Schemathesis (no rompen una HU): " + " · ".join(datos["observaciones"]))
    tr.write_line(f"  Reporte HTML: {datos['reporte']}")


def pytest_terminal_summary(terminalreporter, config):
    _resumen_funcional(terminalreporter)
    _resumen_tecnico(terminalreporter, config)
