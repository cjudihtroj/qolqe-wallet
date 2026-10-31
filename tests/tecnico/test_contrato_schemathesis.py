"""QUÉ ES: la prueba TÉCNICA del pago de deudas (HU-G2-02), generada desde el contrato OpenAPI.

CÓMO FUNCIONA (en cada `pytest`):
  1. Levanta Qolqe en un puerto libre (en un hilo, solo durante esta prueba).
  2. Ejecuta Schemathesis contra /openapi.json, solo para POST /api/servicios/pagos.
     Schemathesis lee el contrato y GENERA casos: válidos, sin campos obligatorios, con
     tipos incorrectos, sin token, con otros métodos HTTP, etc.
  3. Clasifica cada caso por validación de entrada (tests/tecnico/clasificacion_contrato.py),
     regenera reportes/schemathesis/ultimo/reporte.html y deja el resumen para la terminal.
PASA SI: ningún caso devuelve 500 y cada validación recibe la respuesta correcta.
Ejecutar solo esta prueba:  pytest -m schemathesis
MODO: por defecto es DETERMINISTA, así cada ejecución genera los MISMOS casos (reproducible,
ideal para la demo y para comparar antes/después de un arreglo). Para explorar casos nuevos al azar:
  PowerShell:  $env:SCHEMATHESIS_MODO="aleatorio"; pytest -m schemathesis
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import uvicorn

from clasificacion_contrato import analizar, generar_html, resumen
from qolqe.main import app

OPERACION = "POST /api/servicios/pagos"
MAX_EJEMPLOS = 50
CARPETA = Path("reportes/schemathesis/ultimo")


@pytest.fixture(scope="module")
def servidor():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()
    url = f"http://127.0.0.1:{puerto}"
    for _ in range(100):
        try:
            httpx.get(f"{url}/api/salud")
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    httpx.post(f"{url}/api/pruebas/reiniciar", timeout=120)
    yield url
    server.should_exit = True
    hilo.join(timeout=10)


def _ejecutar_schemathesis(url: str, token: str, har: Path) -> str:
    ejecutable = shutil.which("schemathesis", path=str(Path(sys.executable).parent)) or "schemathesis"
    # Determinista = los mismos casos en cada ejecución; "aleatorio" = casos nuevos cada vez
    aleatorio = os.environ.get("SCHEMATHESIS_MODO") == "aleatorio"
    opcion_modo = [] if aleatorio else ["--generation-deterministic"]
    proceso = subprocess.run(
        [ejecutable, "run", f"{url}/openapi.json", "-H", f"Authorization: Bearer {token}",
         "--include-name", OPERACION, "--max-examples", str(MAX_EJEMPLOS), "--no-color",
         "--report", "har", "--report-har-path", str(har), *opcion_modo],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=600,
    )
    return proceso.stdout + proceso.stderr


def _observaciones(salida: str) -> list[str]:
    """Las líneas del bloque 'Failures:' del resumen de Schemathesis (p. ej. 'Invalid Allow header: 1')."""
    lineas, dentro = [], False
    for linea in salida.splitlines():
        texto = linea.strip()
        if texto.startswith("Failures:"):
            dentro = True
        elif dentro and texto.startswith("❌"):
            lineas.append(texto.lstrip("❌ ").strip())
        elif dentro and texto:
            break
    return lineas


@pytest.mark.schemathesis
def test_pagar_deuda_cumple_el_contrato_openapi(servidor, request):
    token = httpx.post(f"{servidor}/api/auth/login", json={"celular": "987654321", "pin": "4826"}).json()["access_token"]
    CARPETA.mkdir(parents=True, exist_ok=True)
    har = CARPETA / "har.json"
    har.unlink(missing_ok=True)

    salida = _ejecutar_schemathesis(servidor, token, har)
    assert har.exists(), f"Schemathesis no generó resultados:\n{salida[-2000:]}"

    casos = analizar(json.loads(har.read_text(encoding="utf-8"))["log"]["entries"])
    semilla = ("aleatorio, semilla " + next((l.split(":", 1)[1].strip() for l in salida.splitlines()
                                             if l.startswith("Seed:")), "?")
               if os.environ.get("SCHEMATHESIS_MODO") == "aleatorio" else "determinista")
    observaciones = _observaciones(salida)
    reporte = CARPETA / "reporte.html"
    reporte.write_text(generar_html(casos, OPERACION, semilla, observaciones, datetime.now().strftime("%Y-%m-%d %H:%M")),
                       encoding="utf-8")

    # Lo lee el resumen de la terminal (tests/conftest.py)
    request.config.resumen_tecnico = {"operacion": OPERACION, "casos": casos, "filas": resumen(casos),
                                      "observaciones": observaciones, "semilla": semilla, "reporte": str(reporte)}

    errores_500 = [c for c in casos if c["estado"] >= 500]
    incorrectos = [c for c in casos if not c["correcto"]]
    assert not errores_500, f"La API se cayó (500) en los casos {[c['numero'] for c in errores_500]}"
    assert not incorrectos, "Respuestas incorrectas: " + "; ".join(
        f"#{c['numero']} {c['validacion']} → {c['estado']}" for c in incorrectos)
