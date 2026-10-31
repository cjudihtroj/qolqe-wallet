<!-- QUÉ ES: reporte de los defectos encontrados por las pruebas (plantilla del curso, llenada).
     Cada DEF tiene regla rota, severidad, pasos para reproducir, esperado vs obtenido y la
     prueba que lo detecta. Al final están las observaciones de Schemathesis (OBS). -->

# Reporte de defectos · Módulo G2 Pago de servicios

Entorno común: Qolqe Wallet 1.0.0 (FastAPI), Python 3.12, Windows 11, `QOLQE_MODO_PRUEBA=1`. Pruebas de API con pytest-bdd + httpx (TestClient). Datos semilla restaurados con `POST /api/pruebas/reiniciar`.

| ID | Título | Regla | Severidad | Prioridad | Pruebas que fallan |
|---|---|---|---|---|---|
| DEF-01 | Se acepta un suministro de 13 dígitos | R-G2-01 | Baja | Media | 1 |
| DEF-02 | Los días de atraso se cuentan con un día de más, así que se cobra mora el mismo día del vencimiento | R-G2-03 | **Alta** | **Alta** | 5 |
| DEF-03 | Una deuda con 60 días de atraso pasa a cobranza y no se puede pagar | R-G2-04 | **Alta** | **Alta** | 2 |
| DEF-04 | El débito automático paga deudas ya vencidas antes de activarlo, y sin mora | HU-G2-05 CA4 | Media | Media | 1 |

---

## DEF-01: Se acepta un código de suministro de 13 dígitos

| Campo | Valor |
|---|---|
| Módulo / regla | G2 · HU-G2-01 CA1 · R-G2-01 (8 a 12 dígitos) |
| Severidad | Baja |
| Prioridad | Media |
| Entorno | Ver arriba |
| Prueba que lo detecta | `tests/api/test_g2_pago_servicios.py::test_longitud_del_código_de_suministro_rg201_8_a_12_dígitos[13 digitos (invalido)...]` |

**Pasos para reproducir**
1. Iniciar sesión como Ana (987654321 / 4826).
2. `GET /api/servicios/deudas?empresa=ELECTRO&suministro=1000000010000` (13 dígitos).

**Resultado esperado:** 422 `SUMINISTRO_INVALIDO`.

**Resultado obtenido:** 404 `SIN_DEUDA_PENDIENTE`. El dato inválido pasa la validación. Lo mismo ocurre al afiliar un servicio.

**Evidencia:** `{"codigo":"SIN_DEUDA_PENDIENTE","detail":"El suministro no tiene deudas pendientes"}`. Causa probable: el límite superior se compara contra `12 + 1` en `validar_suministro` (`qolqe/reglas/servicios.py`). Se detectó con **análisis de valores límite** (12 válido, 13 inválido).

---

## DEF-02: Se cobra mora el mismo día del vencimiento (los días de atraso se cuentan con +1)

| Campo | Valor |
|---|---|
| Módulo / regla | G2 · HU-G2-02 CA1 · HU-G2-01 CA2 · R-G2-03 |
| Severidad | **Alta**: se le cobra de más al cliente |
| Prioridad | **Alta** |
| Entorno | Ver arriba |
| Pruebas que lo detectan | `test_mora_de_05__diario...[el mismo dia del vencimiento]`, `[un dia de atraso]`, `[19 dias, bajo el tope]`, `test_conteo_de_días_de_atraso_alrededor_del_vencimiento[el mismo dia]`, `[un dia despues]` |

**Pasos para reproducir**
1. Reiniciar los datos e iniciar sesión como Ana.
2. `GET /api/servicios/deudas?empresa=ELECTRO&suministro=10000002` (deuda de S/ 85.50 que **vence hoy**).
3. `POST /api/servicios/pagos {"deuda_id": 2}`.

**Resultado esperado:** `dias_atraso = 0`, `mora = "0.00"` y `total = "85.50"`. R-G2-03 dice: "Pagar el mismo día del vencimiento no genera mora".

**Resultado obtenido:** `dias_atraso = 1`, `mora = "0.43"` y `total = "85.93"`. Todos los atrasos se cuentan con un día de más: con 1 día cobra 1.20 en lugar de 0.60, y con 19 días ya aplica el tope de 12.00 en lugar de 11.40.

**Evidencia:** comprobante `{"monto":"85.50","mora":"0.43","total":"85.93",...}`. Causa probable: `dias_de_atraso` suma `+ 1` (`qolqe/reglas/servicios.py`).

---

## DEF-03: Una deuda con 60 días de atraso se envía a cobranza y no se puede pagar

| Campo | Valor |
|---|---|
| Módulo / regla | G2 · HU-G2-01 CA2 · HU-G2-02 CA2 · R-G2-04 |
| Severidad | **Alta**: bloquea un pago que el cliente sí tiene derecho a hacer |
| Prioridad | **Alta** |
| Entorno | Ver arriba |
| Pruebas que lo detectan | `test_estado_de_la_deuda_según_los_días_de_atraso_límite_de_60_días[60-PENDIENTE]`, `test_mora_de_05__diario...[60 dias, aun se puede pagar]` |

**Pasos para reproducir**
1. Reiniciar los datos e iniciar sesión como Ana.
2. `GET /api/servicios/deudas?empresa=INTERNET&suministro=300000000006` (venció hace exactamente 60 días).

**Resultado esperado:** `estado = "PENDIENTE"`, con mora del 10 % y pagable. R-G2-04 dice: "con 60 días todavía se puede".

**Resultado obtenido:** `estado = "EN_COBRANZA"`, `dias_atraso = 61` y `mora = null`. El pago responde 422 `DEUDA_EN_COBRANZA`.

**Evidencia:** `{"id":6,"dias_atraso":61,"mora":null,"total":null,"estado":"EN_COBRANZA"}`. Tiene la misma causa raíz que DEF-02, pero rompe otra regla de negocio y tiene otro impacto, por eso se reporta por separado.

---

## DEF-04: El débito automático paga deudas que ya estaban vencidas (y sin mora)

| Campo | Valor |
|---|---|
| Módulo / regla | G2 · HU-G2-05 CA2 y CA4 (prioridad Media, alcance extra) |
| Severidad | Media: hay un cobro no autorizado al cliente y la empresa pierde la mora |
| Prioridad | Media |
| Entorno | Ver arriba |
| Prueba que lo detecta | `test_las_deudas_ya_vencidas_antes_de_activar_el_débito_no_se_pagan_automáticamente` |

**Pasos para reproducir**
1. Reiniciar los datos e iniciar sesión como Ana.
2. `POST /api/servicios/afiliaciones {"empresa":"ELECTRO","suministro":"10000003","alias":"Luz vencida"}` (deuda vencida ayer).
3. `PUT /api/servicios/afiliaciones/{id} {"debito_automatico": true}`.
4. `POST /api/pruebas/procesar-diario`.

**Resultado esperado:** `debitos_pagados = 0`. Solo se pagan las deudas que vencen **ese día**, y las vencidas antes de activar el débito no se pagan.

**Resultado obtenido:** `debitos_pagados = 1`. Se pagó la deuda vencida, con origen `DEBITO_AUTOMATICO`, `mora = 0.00` y `total = 200.00`, aunque la consulta mostraba un total de 202.00.

**Evidencia:** `{"debitos_pagados":1,...}` y `GET /api/servicios/pagos` muestra el pago. Causa probable: el proceso diario filtra `vencimiento <= hoy` en lugar de `= hoy`.

---

## Observaciones de las pruebas técnicas (Schemathesis): no son defectos funcionales

| ID | Hallazgo | Clasificación |
|---|---|---|
| OBS-01 | `GET /api/servicios/pagos?afiliacion_id=-1072...` (entero muy grande) responde **422**, pero el contrato declara `integer` sin rango. | Defecto **del contrato**: falta documentar el rango (`minimum`/`maximum`). Severidad baja. |
| OBS-02 | `OPTIONS /api/servicios/pagos` responde `Allow: POST`, aunque la ruta también acepta `GET`. | Convención HTTP (cabecera `Allow` incompleta). Observación de baja severidad, la produce el framework. |

Resultado positivo: en 423 solicitudes generadas **no hubo ningún 500**.
