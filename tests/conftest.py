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

import pytest

os.environ.setdefault("QOLQE_BD", "datos/pruebas.db")
os.environ.setdefault("QOLQE_MODO_PRUEBA", "1")

# FALLOS ESPERADOS: pruebas que fallan A PROPÓSITO porque detectan un defecto ya reportado en
# docs/defectos.md. Se marcan como "xfail" (fallo esperado) con el ID del defecto:
#   - el pipeline queda en VERDE, pero el defecto sigue VISIBLE en el reporte (sale como xfailed);
#   - strict=True: si alguien arregla el defecto y la prueba empieza a pasar, pytest lo marca como
#     FALLO (XPASS) para avisar que hay que actualizar esta lista y cerrar el defecto.
# Formato: fragmento del nombre de la prueba → defecto. Un fallo que no esté aquí es "NUEVO":
# rompe el pipeline y hay que analizarlo (posible regresión o defecto nuevo).
DEFECTOS_CONOCIDOS = [
    ("[13 digitos (invalido)-", "DEF-01"),
    ("conteo_de_días_de_atraso_alrededor_del_vencimiento[el mismo dia-", "DEF-02"),
    ("conteo_de_días_de_atraso_alrededor_del_vencimiento[un dia despues-", "DEF-02"),
    ("[el mismo dia del vencimiento-", "DEF-02"),
    ("[un dia de atraso-", "DEF-02"),
    ("[19 dias, bajo el tope-", "DEF-02"),
    ("[60-PENDIENTE]", "DEF-03"),
    ("[60 dias, aun se puede pagar-", "DEF-03"),
    ("ya_vencidas_antes_de_activar", "DEF-04"),
]
TECNICAS = ["camino-feliz", "particion", "valor-limite", "efecto", "concurrencia", "seguridad", "tecnico", "contrato", "schemathesis"]

_etiquetas: dict[str, set[str]] = {}
_resultados: dict[str, dict] = {}


def pytest_configure(config):
    config.addinivalue_line("markers", "schemathesis: prueba técnica generada con Schemathesis desde el contrato OpenAPI")


def pytest_collection_modifyitems(items):
    for item in items:
        etiquetas = {m.name for m in item.iter_markers()} - {"parametrize", "usefixtures", "xfail"}
        _etiquetas[item.nodeid] = etiquetas
        # Etiquetas del .feature (@HU-G2-02, @CA1, @valor-limite...) dentro del JUnit XML:
        # así el pipeline puede armar la matriz de trazabilidad HU → caso → resultado.
        item.user_properties.append(("etiquetas", ",".join(sorted(etiquetas))))
        defecto = _defecto(item.nodeid)
        if not defecto.startswith("NUEVO"):
            item.add_marker(pytest.mark.xfail(reason=f"{defecto} (ver docs/defectos.md)", strict=True))
            item.user_properties.append(("defecto", defecto))


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        mensaje = ""
        if hasattr(report, "wasxfail"):
            # Fallo esperado: falló como se esperaba (xfailed) o pasó sin esperarlo (XPASS strict).
            _resultados[report.nodeid] = {"estado": "xfailed" if report.skipped else "failed",
                                          "mensaje": report.wasxfail or "XPASS: el defecto parece corregido"}
            return
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
    por_hu = defaultdict(lambda: [0, 0, 0])
    por_tecnica = defaultdict(lambda: [0, 0, 0])
    for nodeid, r in funcionales.items():
        etiquetas = _etiquetas.get(nodeid, set())
        hu = sorted(e for e in etiquetas if e.startswith("HU-")) or ["(sin HU: humo)"]
        indice = {"passed": 0, "xfailed": 1}.get(r["estado"], 2)
        por_hu[hu[0]][indice] += 1
        for tecnica in TECNICAS:
            if tecnica in etiquetas:
                por_tecnica[tecnica][indice] += 1
    tr.write_line(f"  {'Historia de usuario':<22}{'Casos':>7}{'Pasan':>7}{'Esperado':>10}{'Fallan':>8}")
    for hu in sorted(por_hu):
        ok, xf, ko = por_hu[hu]
        tr.write_line(f"  {hu:<22}{ok + xf + ko:>7}{ok:>7}{xf:>10}{ko:>8}")
    ok, xf, ko = (sum(v[i] for v in por_hu.values()) for i in range(3))
    tr.write_line(f"  {'TOTAL':<22}{ok + xf + ko:>7}{ok:>7}{xf:>10}{ko:>8}")
    tr.write_line("  (Esperado = fallo esperado: la prueba detecta un defecto ya reportado)")
    tr.write_line("")
    tr.write_line("  Por técnica: " + " · ".join(
        f"{t} {v[0]}/{sum(v)}" for t, v in ((t, por_tecnica[t]) for t in TECNICAS) if sum(v)))
    fallos = [(n, r) for n, r in funcionales.items() if r["estado"] != "passed"]
    if fallos:
        tr.write_line("")
        tr.write_line("  Fallos esperados (cada uno evidencia un defecto) y fallos nuevos:")
        for nodeid, r in sorted(fallos, key=lambda x: _defecto(x[0])):
            marca = _defecto(nodeid) if r["estado"] == "xfailed" else "NUEVO, analizar"
            tr.write_line(f"   [{marca}] {_nombre(nodeid)[:95]}")
            if r["mensaje"]:
                tr.write_line(f"            {r['mensaje'][:110]}")
        nuevos = sum(1 for _, r in fallos if r["estado"] != "xfailed")
        defectos = sorted({_defecto(n) for n, _ in fallos} - {"NUEVO, analizar"})
        tr.write_line("")
        tr.write_line(f"  {len(fallos) - nuevos} fallos esperados → defectos conocidos: {', '.join(defectos) or 'ninguno'}"
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
