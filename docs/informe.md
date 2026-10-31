<!-- QUÉ ES: informe del proyecto (copia de docs/plantilla-informe.md, como pide el curso).
     Para la Entrega 1 están llenas las secciones 1 (alcance), 2 (pruebas de API:
     herramienta, diseño, resultados, trazabilidad) y 5 (defectos). Las 3, 4 y 6 son
     de las siguientes entregas. -->

# Informe del proyecto – Grupo G2 (individual)

## 1. Datos generales y alcance

| Campo | Valor |
|---|---|
| Integrantes | David Marcelo (trabajo individual) |
| Módulo | **G2 · Pago de servicios y afiliaciones** |
| Herramienta de API | **pytest + pytest-bdd + httpx** (funcionales) y **Schemathesis** (técnicas, desde el contrato OpenAPI) |
| Herramienta web | **Robot Framework + Browser Library** (Playwright) |
| Herramienta de rendimiento | (Parte 3) |

**Alcance y nivel de prueba.** El nivel es **prueba de API**, que también es prueba de integración de componentes. Se envían solicitudes HTTP a la interfaz pública y se verifican el estado, el cuerpo, el contrato y el efecto.

| HU | Prioridad | Cobertura | Por qué |
|---|---|---|---|
| HU-G2-01 Consultar deudas | **Alta** | Todos los CA (CA1 a CA3) | Es la puerta de entrada al pago: muestra la mora y el estado de cobranza |
| HU-G2-02 Pagar una deuda | **Alta** | Todos los CA (CA1 a CA4) | Mueve dinero: mora, saldo, doble pago y concurrencia |
| HU-G2-07 Comprobantes | Media | Solo CA2 (seguridad: comprobante de otro usuario → 404) | Es un riesgo de fuga de datos financieros |
| HU-G2-05 Débito automático | Media | CA2 y CA4 (extra) | Lo ejecuta el Sistema y cobra sin intervención del usuario |
| HU-G2-03, 04 y 06 | Media/Baja | Fuera de alcance en la Entrega 1 | Se priorizó por riesgo (trabajo individual) |

**Criterio para decidir:** prioridad **por riesgo**. Primero lo que afecta dinero o seguridad (Alta), luego lo que el sistema hace solo (débito) y al final la comodidad.

## 2. Pruebas de API

### Herramienta
- **pytest-bdd** ejecuta los escenarios **Gherkin** (`features/*.feature`, escritos en español) a partir de las HU. Cada frase se conecta con un paso en Python (`tests/api/conftest.py`). Así el `.feature` es a la vez documentación y prueba (documentación viva y trazable).
- **httpx / TestClient** envía las solicitudes HTTP a la app FastAPI dentro del mismo proceso, sin levantar un servidor, así que la ejecución es rápida y estable.
- La **API de soporte** (`/api/pruebas/*`) permite reiniciar los datos (independencia, la "I" de FIRST), **fijar el reloj** (para probar la mora por día exacto) y **fijar el saldo** (para los valores límite de RN-08).
- **Schemathesis** lee `/openapi.json` y genera cientos de solicitudes (pruebas basadas en propiedades: nunca un 500, respuestas conformes al esquema, datos válidos aceptados y datos inválidos rechazados).

Comparación y justificación: ver la presentación, slides 2 y 3.

### Diseño de casos
| Técnica | Aplicada a |
|---|---|
| Partición de equivalencia | Empresa existente/inexistente; suministro numérico/no numérico; con deuda/sin deuda; con token/sin token; deuda pendiente/pagada/en cobranza/inexistente; propietario/otro usuario |
| Análisis de valores límite | Suministro de 7, 8, 12 y 13 dígitos; días de atraso -1, 0 y 1; tope de mora en 19, 20 y 21 días; cobranza en 59, 60 y 61 días; saldo igual al total o 1 céntimo menos |
| Verificación de efecto / sin efecto | Saldo después de pagar; saldo sin cambio ante un error; el movimiento con el mismo código (RN-10); la deuda desaparece de pendientes |
| Concurrencia | 2 pagos simultáneos de la misma deuda → 1 éxito y 1 con 409 |
| Técnicas (contrato) | Tipo inválido de `deuda_id`, cuerpo vacío y fuzzing con Schemathesis |

### Cómo ejecutar
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -v                                               # funcionales
pytest --html=reportes/pytest/reporte.html --self-contained-html
pytest -m "HU-G2-02"                                    # solo una HU (tags del .feature)
# técnicas (con la app levantada: uvicorn qolqe.main:app)
schemathesis run http://localhost:8000/openapi.json -H "Authorization: Bearer <token>" --include-path-regex "api/servicios/(deudas|pagos)" --max-examples 30
```

### Resultados (17/10/2026)
| Tipo | Casos | Pasan | Fallan | Hallazgos |
|---|---|---|---|---|
| Funcionales (pytest-bdd, 41 de G2 + 1 de humo) | 42 | 33 | 9 | 4 defectos (DEF-01 a DEF-04) |
| Técnicos (Schemathesis, 4 operaciones) | 423 generados | 421 | 2 | 2 observaciones (OBS-01 y OBS-02), **0 errores 500** |

### Trazabilidad HU → escenarios → resultado
| HU / CA | Escenarios (.feature) | Resultado |
|---|---|---|
| HU-G2-01 CA1 | Empresa inexistente; longitud de suministro (4 casos); caracteres no numéricos (3 casos) | ❌ 13 dígitos → DEF-01 |
| HU-G2-01 CA2 | Orden; campos y titular enmascarado; estado 59/60/61 días; conteo de atraso -1/0/1 | ❌ 60 días → DEF-03; ❌ conteo de 0 y 1 → DEF-02 |
| HU-G2-01 CA3 | Sin deudas; sin deudas después de pagar | ✅ |
| HU-G2-02 CA1 | Pago exitoso; mora (7 valores límite); saldo exacto o insuficiente | ❌ 0, 1 y 19 días → DEF-02; ❌ 60 días → DEF-03 |
| HU-G2-02 CA2 | Deuda inexistente, ya pagada o en cobranza | ✅ |
| HU-G2-02 CA3 | Pagos simultáneos | ✅ |
| HU-G2-02 CA4 | Campos del comprobante; movimiento con el mismo código | ✅ |
| HU-G2-07 CA2 | Comprobante de otro usuario → 404 | ✅ |
| HU-G2-05 CA2 / CA4 | El débito paga el día del vencimiento / no paga deudas ya vencidas | ✅ / ❌ DEF-04 |
| Seguridad / técnico | Sin token → 401; `deuda_id` inválido → 422 | ✅ |

Evidencia: `reportes/pytest/reporte.html` y `reportes/schemathesis/`.

## 3. Pruebas web y CI/CD

### Pruebas web (E2E)
| Campo | Valor |
|---|---|
| Herramienta | **Robot Framework + Browser Library** (Playwright, Chromium) |
| Criterio para elegir qué va por web | Por web va lo que el usuario **ve y hace en pantalla** (flujo completo y comprobante). Los cálculos y casos técnicos (mora por día, concurrencia, seguridad, contrato) se quedan en la API, que es más rápida y estable (pirámide de pruebas) |
| Alcance | 3 casos: CP-W01 pagar luz (HU-G2-01 + HU-G2-02 CA1/CA4), CP-W02 pagar agua (ídem), CP-W03 afiliar un servicio (HU-G2-03 CA1) |

**Patrón mantenible: Page Object en 3 capas.** (1) El caso dice **qué** se prueba en Given/When/Then; (2) las keywords de negocio traducen cada paso; (3) los Page Objects (`tests/e2e/pages/`) saben **cómo** se usa cada pantalla (localizadores `data-testid` + acciones). Si una pantalla cambia, se corrige un solo archivo. A gran escala la alternativa es **Screenplay** (actores, tareas, preguntas); para este alcance agregaría complejidad sin beneficio.

**Sin esperas fijas.** No hay `Sleep`: las aserciones de Browser reintentan solas hasta 10 s y se espera por **condición** (elemento visible, contador cargado). Cada prueba reinicia los datos por API (independencia).

**Estabilidad: pasa 3 veces seguidas.** El pipeline corre la suite web **3 veces seguidas en cada run**; si una sola falla, el job falla.

### Pipeline de CI/CD (GitHub Actions)
| Archivo | Rol |
|---|---|
| `.github/workflows/pruebas.yml` | Orquestador. Eventos: push a `main`, pull request a `main` y manual (elige `todas`, `api` o `web`) |
| `.github/workflows/_api.yml` | Reutilizable: pytest-bdd + Schemathesis → JUnit XML + HTML + resumen |
| `.github/workflows/_web.yml` | Reutilizable: levanta Qolqe, corre Robot 3 veces seguidas → report/log + capturas + resumen |
| `.github/scripts/` | `resumen.py` (resumen en la página del run), `trazabilidad.py` (matriz), `portada.py` (portada de reportes) |

Orden (*fail fast*): **api → web → reportes**. Si la API falla, la web se omite. El job `reportes` (solo en `main`) publica toda la evidencia en **GitHub Pages**: https://deyvydt.github.io/qolqe-wallet-services/

**Quality gate.** Todas las pruebas pasan, salvo los fallos esperados ligados a un defecto reportado (`xfail strict` con su `DEF-0X`). Si un defecto se corrige, la prueba pasa sin esperarlo (XPASS) y el pipeline se pone rojo para actualizar la lista. Un fallo no listado es nuevo y también bloquea. La rama `main` está protegida: un PR no se fusiona si el pipeline no está en verde.

**Trazabilidad.** Las etiquetas `@HU-G2-xx @CAx` del Gherkin y `HU-G2-xx CP-Wxx` de Robot viajan en el JUnit XML / output.xml; el pipeline genera en cada run la matriz HU → caso → nivel → resultado → defecto (`trazabilidad.html` en Pages, resumen del run y `docs/trazabilidad.md`).

## 4. Pruebas de rendimiento
*(Parte 3)*

## 5. Defectos encontrados

| ID | Título | Severidad | Estado |
|---|---|---|---|
| DEF-01 | Se acepta un suministro de 13 dígitos (R-G2-01) | Baja | Abierto |
| DEF-02 | Se cobra mora el mismo día del vencimiento: los días de atraso se cuentan +1 (R-G2-03) | Alta | Abierto |
| DEF-03 | Una deuda con 60 días pasa a cobranza y no se puede pagar (R-G2-04) | Alta | Abierto |
| DEF-04 | El débito automático paga deudas ya vencidas y sin mora (HU-G2-05 CA4) | Media | Abierto |

El detalle está en `docs/defectos.md`.

## 6. Conclusiones y recomendaciones
*(Entrega final)*
