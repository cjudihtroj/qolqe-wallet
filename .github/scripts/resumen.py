"""QUÉ ES: escribe el RESUMEN de una ejecución de pruebas en la página del run de GitHub Actions.

PARA QUÉ:
  Al abrir un run en GitHub se ve, sin descargar nada, cuántas pruebas pasaron, cuántas
  fallan por un defecto ya conocido (DEF-0X), cuántas fallan de verdad y cuántas se omitieron,
  separado por historia de usuario (HU). Sirve para los dos tipos de resultado:
    - JUnit XML de pytest (pruebas de API y de contrato).
    - output.xml de Robot Framework (pruebas web).
  El script detecta solo de qué tipo es el archivo. Si el archivo no existe, lo dice
  ("no ejecutado") en lugar de romperse.
  Siempre termina con éxito (exit 0): si el run pasa o falla lo decide el paso de pruebas,
  no este script.

CÓMO SE USA (desde la raíz del repo):
  python .github/scripts/resumen.py reportes/api/junit.xml --titulo "Pruebas de API"
  python .github/scripts/resumen.py reportes/web/output.xml --titulo "Pruebas web (E2E)"
  Escribe en el archivo de la variable GITHUB_STEP_SUMMARY; fuera de GitHub lo imprime en pantalla.
  Reutiliza la lectura de resultados de trazabilidad.py (misma carpeta).
"""
import argparse
import sys
from collections import defaultdict

from trazabilidad import SIN_HU, agregar_a_summary, contar, contexto_run, leer_reporte, url_defecto


def _md(texto):
    return str(texto).replace("|", "\\|").replace("\n", " ")


def generar(ruta, titulo):
    tipo, casos = leer_reporte(ruta)
    out = [f"## {titulo}", ""]
    if casos is None:
        out += [f"⏭️ **No ejecutado:** no se encontró un resultado válido en `{ruta}`.", ""]
        return "\n".join(out)

    origen = "Robot Framework" if tipo == "robot" else "pytest"
    total = contar(casos)
    out += [f"Fuente: `{ruta}` ({origen}) · {len(casos)} casos", "",
            "| Resultado | Casos |", "|---|---:|",
            f"| ✅ Pasan | {total['passed']} |",
            f"| ⚠️ Fallos esperados (defectos conocidos) | {total['xfailed']} |",
            f"| ❌ Fallan | {total['failed']} |",
            f"| ⏭️ Omitidas | {total['skipped']} |", ""]

    # Tabla por HU (un caso que cubre dos HU cuenta en las dos)
    por_hu = defaultdict(lambda: defaultdict(int))
    for c in casos:
        for hu in c["hu"]:
            por_hu[hu]["casos"] += 1
            por_hu[hu][c["estado"]] += 1
    if por_hu:
        out += ["| HU | Casos | ✅ Pasan | ⚠️ Fallo esperado | ❌ Fallan |", "|---|---:|---:|---:|---:|"]
        for hu in sorted(por_hu, key=lambda h: (h == SIN_HU, h)):
            d = por_hu[hu]
            out.append(f"| {hu} | {d['casos']} | {d['passed']} | {d['xfailed']} | {d['failed']} |")
        out.append("")

    url_defectos = contexto_run()["url_defectos"]
    esperados = [c for c in casos if c["estado"] == "xfailed"]
    if esperados:
        out += [f"### ⚠️ Fallos esperados ({len(esperados)})",
                "Estas pruebas fallan a propósito: detectan defectos ya reportados en "
                f"[docs/defectos.md]({url_defectos}).", ""]
        for c in sorted(esperados, key=lambda c: (c["defecto"], c["nombre"])):
            defecto = f"[{c['defecto']}]({url_defecto(c['defecto'], url_defectos)})" if c["defecto"] else "sin ID"
            out.append(f"- **{defecto}** · {_md(_nombre(c))}")
        out.append("")

    fallos = [c for c in casos if c["estado"] == "failed"]
    if fallos:
        out += [f"### ❌ Fallos reales ({len(fallos)})", "Fallos nuevos: hay que analizarlos (posible regresión o defecto nuevo).", ""]
        for c in sorted(fallos, key=lambda c: c["nombre"]):
            detalle = f" — `{_md(c['mensaje'][:150])}`" if c["mensaje"] else ""
            out.append(f"- {_md(_nombre(c))}{detalle}")
        out.append("")
    elif not esperados and total["passed"]:
        out += ["Todas las pruebas ejecutadas pasan. 🎉", ""]
    return "\n".join(out)


def _nombre(c):
    return f"{c['cp']} · {c['nombre']}" if c["cp"] else c["nombre"]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Escribe el resumen de un reporte de pruebas en GITHUB_STEP_SUMMARY.")
    p.add_argument("ruta_xml", help="JUnit XML de pytest u output.xml de Robot Framework")
    p.add_argument("--titulo", default="Resultado de pruebas", help="título de la sección")
    args = p.parse_args()
    try:
        agregar_a_summary(generar(args.ruta_xml, args.titulo))
    except Exception as error:  # nunca romper el pipeline por el resumen
        print(f"Aviso: no se pudo generar el resumen de {args.ruta_xml}: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
