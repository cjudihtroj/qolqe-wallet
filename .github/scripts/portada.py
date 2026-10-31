"""QUÉ ES: genera la PORTADA (index.html) del sitio de GitHub Pages con la evidencia de pruebas.

PARA QUÉ:
  Es la página de entrada para quien revisa el proyecto (docente, público): explica en una
  frase cada reporte y enlaza a él. Solo muestra los reportes que existen en la carpeta
  (si en un run no se corrió la web, no aparece un enlace roto). Muestra además el número de
  run, el commit, la rama, la fecha (hora de Lima) y el enlace al run de GitHub Actions.
  Usa el mismo estilo visual que la matriz de trazabilidad (modo claro y oscuro).

CÓMO SE USA (desde la raíz del repo, cuando la carpeta del sitio ya tiene los reportes):
  python .github/scripts/portada.py --sitio sitio
  Busca dentro de la carpeta: api/reporte.html, contrato/reporte.html, web/report.html,
  web/log.html y trazabilidad.html. Escribe <carpeta>/index.html.
  Reutiliza el estilo y los datos del run de trazabilidad.py (misma carpeta).
"""
import argparse
import sys
from pathlib import Path

from trazabilidad import contexto_run, esc, pagina_html

# (archivo dentro del sitio, ícono, título, explicación para un público no técnico)
REPORTES = [
    ("trazabilidad.html", "🧭", "Matriz de trazabilidad",
     "Muestra qué historia de usuario cubre cada prueba y cómo le fue en esta ejecución. Es el mejor punto de partida."),
    ("api/reporte.html", "🔌", "Pruebas de API (reglas de negocio)",
     "Verifican las reglas del pago de servicios (montos, mora, límites, afiliaciones) hablando directo con el servidor, sin pantalla."),
    ("contrato/reporte.html", "📜", "Pruebas de contrato (Schemathesis)",
     "Una herramienta genera cientos de peticiones automáticas a partir de la especificación de la API para buscar respuestas inesperadas."),
    ("web/report.html", "🖥️", "Pruebas web de punta a punta · Reporte",
     "Un robot abre el navegador y usa la app como lo haría una persona: inicia sesión, consulta y paga. Aquí está el resumen."),
    ("web/log.html", "🔎", "Pruebas web de punta a punta · Detalle paso a paso",
     "El mismo recorrido del robot, paso por paso, con capturas de pantalla para ver exactamente qué pasó."),
]

CSS_EXTRA = """
.reportes{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
a.reporte{display:block;background:var(--tarjeta);border:1px solid var(--borde);border-radius:14px;padding:18px;
color:var(--texto);text-decoration:none;transition:transform .12s,border-color .12s}
a.reporte:hover{transform:translateY(-2px);border-color:var(--marca)}
a.reporte .icono{font-size:1.8rem}
a.reporte h3{margin:6px 0 4px;font-size:1.05rem;color:var(--marca)}
a.reporte p{margin:0;color:var(--suave);font-size:.93rem}
a.reporte.destacado{border:2px solid var(--marca)}
"""


def generar(sitio):
    ctx = contexto_run()
    tarjetas = []
    for archivo, icono, titulo, texto in REPORTES:
        if (sitio / archivo).is_file():
            clase = "reporte destacado" if archivo == "trazabilidad.html" else "reporte"
            tarjetas.append(f"<a class='{clase}' href='{esc(archivo)}'><div class='icono'>{icono}</div>"
                            f"<h3>{esc(titulo)}</h3><p>{esc(texto)}</p></a>")
    if tarjetas:
        cuerpo = ("<h2>Reportes de esta ejecución</h2><p class='ayuda'>Haz clic en un reporte para abrirlo. "
                  "Todos se generaron automáticamente en el mismo run.</p>"
                  f"<div class='reportes'>{''.join(tarjetas)}</div>")
    else:
        cuerpo = "<h2>Reportes de esta ejecución</h2><p class='ayuda'>Este run no generó reportes.</p>"
    cuerpo += ("<h2>¿Qué es esto?</h2><p class='ayuda'>Qolqe es una billetera digital. Este sitio reúne la evidencia "
               "de las pruebas del módulo G2 <b>Pago de servicios</b> (luz, agua, internet): se vuelven a ejecutar "
               "solas cada vez que cambia el código, y esta página siempre muestra la última ejecución.</p>")
    pagina = pagina_html("Qolqe · G2 Pago de servicios · Evidencia de pruebas",
                         "Resultados automáticos de las pruebas del módulo de pago de servicios.", ctx, cuerpo)
    return pagina.replace("</style>", CSS_EXTRA + "</style>", 1), len(tarjetas)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Genera la portada index.html del sitio de GitHub Pages.")
    p.add_argument("--sitio", required=True, help="carpeta del sitio (p. ej. sitio)")
    args = p.parse_args()
    sitio = Path(args.sitio)
    sitio.mkdir(parents=True, exist_ok=True)
    pagina, cantidad = generar(sitio)
    (sitio / "index.html").write_text(pagina, encoding="utf-8")
    print(f"Portada: {sitio / 'index.html'} ({cantidad} reportes enlazados)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
