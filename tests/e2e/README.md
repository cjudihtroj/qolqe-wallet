# E2E · G2 Pago de servicios con Robot Framework + Browser Library

Automatización del **happy path** del módulo G2 de Qolqe por la interfaz web:

> Ana inicia sesión → va a *Pagar servicios* → consulta la deuda ELECTRO `10000001` → paga S/ 120.00 → el comprobante muestra el pago y el saldo nuevo (S/ 1,380.00).

Cubre **HU-G2-01** (consultar deuda) y **HU-G2-02** (pagar deuda, CA1 y CA4).

## Estructura (patrón Page Object + Fixtures)

```
tests/e2e/
├── pago_servicios.robot        ¿QUÉ se prueba? Caso en estilo Given/When/Then
├── afiliacion_ia.robot         Caso generado con IA (HU-G2-03) y revisado por el equipo
├── pago_agua_ia.robot          Caso generado EN VIVO con Claude Code + rf-mcp y refactorizado
├── pages/
│   ├── LoginPage.resource      ¿CÓMO se usa /login?    (localizadores + acciones)
│   └── ServiciosPage.resource  ¿CÓMO se usa /servicios?
└── resources/
    └── Comun.resource          Fixtures: abrir navegador + reiniciar datos / cerrar
```

Flujo de una ejecución: **caso → paso (Given/When/Then) → Page Object → Browser Library → Playwright → navegador**.

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Python | 3.11+ | Qolqe y Robot Framework |
| Node.js | 20 o 22 LTS | Browser Library usa Playwright, que corre en Node |

## Instalación (una sola vez)

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-e2e.txt
rfbrowser init chromium                # descarga Playwright + Chromium
```

## Ejecución

**Terminal 1** – levantar Qolqe:

```bash
uvicorn qolqe.main:app
```

**Terminal 2** – correr las pruebas:

```bash
robot --outputdir results tests/e2e                         # sin ventana (headless)
robot --outputdir results -v HEADLESS:False tests/e2e       # viendo el navegador (demo)
robot --outputdir results -v HEADLESS:False -v SLOWMO:1s tests/e2e   # demo en cámara lenta
```

Resultado esperado: `3 tests, 3 passed, 0 failed`.

> **Windows / terminal de VS Code:** si Robot falla con `RecursionError` o `LookupError: unknown encoding: utf-8:surrogateescape`, es porque VS Code define `PYTHONIOENCODING=utf-8:surrogateescape`. Antes de correr `robot`, ejecuta en PowerShell:
>
> ```powershell
> $env:PYTHONIOENCODING='utf-8'
> ```

## Capacidad de IA

`afiliacion_ia.robot` se generó con un asistente de IA a partir de este pedido:

> Este es el Page Object `ServiciosPage.resource` de Robot Framework con Browser Library. Escribe un caso de prueba nuevo para la historia HU-G2-03: Ana afilia el servicio AGUA con suministro 20000004 y alias "Agua mamá", y verifica que aparece en la lista de afiliaciones. Usa los data-testid `select-afiliacion-empresa`, `input-afiliacion-suministro`, `input-afiliacion-alias`, `boton-afiliar` y `lista-afiliaciones`. Reutiliza las keywords existentes.

Lo que corregimos: la primera versión era **frágil** (fallaba a veces) porque escribía antes de que la pantalla terminara de cargar. Se arregló en el Page Object (`Ir A Pagar Servicios` espera el contador de afiliaciones). Después pasó 5 de 5.

## Evidencia

| Archivo | Qué contiene |
|---|---|
| `results/report.html` | Resumen: qué pasó y qué falló |
| `results/log.html` | Cada keyword paso a paso, con la captura final (dentro de cada TEST → Teardown → `Take Screenshot`) |
| `results/browser/screenshot/` | Captura de la pantalla al terminar (un `.png` por prueba) |
| `results/browser/traces/` | Traza Playwright (solo si falla): `npx playwright show-trace <archivo.zip>` |

## Decisiones de diseño

- **Localizadores `data-testid`**: Qolqe los expone en todos los elementos; no dependen del texto ni del estilo.
- **Sin `Sleep`**: las aserciones de Browser (`Get Text … ==`, `Get Url … contains`) reintentan solas hasta 10 s.
- **Datos independientes (FIRST)**: cada prueba reinicia los datos con `POST /api/pruebas/reiniciar` antes de empezar.
