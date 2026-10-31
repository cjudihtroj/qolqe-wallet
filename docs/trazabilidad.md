<!-- QUÉ ES: matriz de trazabilidad generada automáticamente por .github/scripts/trazabilidad.py.
     No editar a mano: se vuelve a generar en cada ejecución del pipeline. -->

# Matriz de trazabilidad · G2 Pago de servicios

Run #local · commit `local` · rama `local` · 31/10/2026 14:46 (hora de Lima)

Cada fila une una **historia de usuario (HU)** con el **caso de prueba** que la verifica, el **nivel** donde se prueba y el **resultado de esta ejecución**.

**Totales:** ✅ 37 pasan · ⚠️ 9 fallos esperados (defectos conocidos) · ❌ 0 fallan · ⏭️ 0 omitidas

Fuentes: API ✔️ ejecutada · Web ✔️ ejecutada

## Cobertura de la especificación

| HU | Descripción | ¿Tiene casos en este run? | Casos |
|---|---|---|---:|
| HU-G2-01 | Consultar deudas | ✅ Sí | 21 |
| HU-G2-02 | Pagar una deuda | ✅ Sí | 22 |
| HU-G2-03 | Afiliar un servicio | ✅ Sí | 1 |
| HU-G2-04 | Ver servicios afiliados | ➖ Fuera de alcance | 0 |
| HU-G2-05 | Editar afiliación y débito automático | ✅ Sí | 2 |
| HU-G2-06 | Desafiliar | ➖ Fuera de alcance | 0 |
| HU-G2-07 | Ver pagos y comprobantes | ✅ Sí | 1 |

**5 de 7 HU** del módulo tienen casos en este run.

## Resumen por HU

| HU | Casos | Cobertura por nivel | ✅ | ⚠️ | ❌ | ⏭️ | Defectos | Estado |
|---|---:|---|---:|---:|---:|---:|---|---|
| HU-G2-01 | 21 | api 19 · web 2 | 17 | 4 | 0 | 0 | [DEF-01](defectos.md#def-01-se-acepta-un-código-de-suministro-de-13-dígitos), [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1), [DEF-03](defectos.md#def-03-una-deuda-con-60-días-de-atraso-se-envía-a-cobranza-y-no-se-puede-pagar) | ✅ OK (con defectos conocidos) |
| HU-G2-02 | 22 | api 20 · web 2 | 18 | 4 | 0 | 0 | [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1), [DEF-03](defectos.md#def-03-una-deuda-con-60-días-de-atraso-se-envía-a-cobranza-y-no-se-puede-pagar) | ✅ OK (con defectos conocidos) |
| HU-G2-03 | 1 | web 1 | 1 | 0 | 0 | 0 | — | ✅ OK |
| HU-G2-05 | 2 | api 2 | 1 | 1 | 0 | 0 | [DEF-04](defectos.md#def-04-el-débito-automático-paga-deudas-que-ya-estaban-vencidas-y-sin-mora) | ✅ OK (con defectos conocidos) |
| HU-G2-07 | 1 | api 1 | 1 | 0 | 0 | 0 | — | ✅ OK |
| (sin HU) | 2 | api 1 · contrato 1 | 2 | 0 | 0 | 0 | — | ✅ OK |

## Matriz HU → caso → nivel → resultado

| HU | Caso de prueba | CA | Nivel | Resultado |
|---|---|---|---|---|
| HU-G2-01 | cada deuda muestra todos sus datos y el titular enmascarado | CA2 | api | ✅ passed |
| HU-G2-01 | consultar deudas sin token | — | api | ✅ passed |
| HU-G2-01 | conteo de días de atraso alrededor del vencimiento [el mismo dia-0-0] | CA2 | api | ⚠️ xfailed → [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1) |
| HU-G2-01 | conteo de días de atraso alrededor del vencimiento [un dia antes--1-0] | CA2 | api | ✅ passed |
| HU-G2-01 | conteo de días de atraso alrededor del vencimiento [un dia despues-1-1] | CA2 | api | ⚠️ xfailed → [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1) |
| HU-G2-01 | después de pagar la única deuda el suministro queda sin deudas pendientes | CA3 | api | ✅ passed |
| HU-G2-01 | deudas ordenadas de la más antigua a la más reciente | CA2 | api | ✅ passed |
| HU-G2-01 | empresa inexistente | CA1 | api | ✅ passed |
| HU-G2-01 | estado de la deuda según los días de atraso límite de 60 días [59-PENDIENTE] | CA2 | api | ✅ passed |
| HU-G2-01 | estado de la deuda según los días de atraso límite de 60 días [60-PENDIENTE] | CA2 | api | ⚠️ xfailed → [DEF-03](defectos.md#def-03-una-deuda-con-60-días-de-atraso-se-envía-a-cobranza-y-no-se-puede-pagar) |
| HU-G2-01 | estado de la deuda según los días de atraso límite de 60 días [61-EN_COBRANZA] | CA2 | api | ✅ passed |
| HU-G2-01 | longitud del código de suministro rg201 8 a 12 dígitos [12 digitos (limite max)-INTERNET-300000000007-200--] | CA1 | api | ✅ passed |
| HU-G2-01 | longitud del código de suministro rg201 8 a 12 dígitos [13 digitos (invalido)-ELECTRO-1000000010000-422-SUMINISTRO_INVALIDO] | CA1 | api | ⚠️ xfailed → [DEF-01](defectos.md#def-01-se-acepta-un-código-de-suministro-de-13-dígitos) |
| HU-G2-01 | longitud del código de suministro rg201 8 a 12 dígitos [7 digitos (invalido)-ELECTRO-1234567-422-SUMINISTRO_INVALIDO] | CA1 | api | ✅ passed |
| HU-G2-01 | longitud del código de suministro rg201 8 a 12 dígitos [8 digitos (limite min)-ELECTRO-10000001-200--] | CA1 | api | ✅ passed |
| HU-G2-01 | suministro con caracteres no numéricos [-10000001] | CA1 | api | ✅ passed |
| HU-G2-01 | suministro con caracteres no numéricos [1000 0001] | CA1 | api | ✅ passed |
| HU-G2-01 | suministro con caracteres no numéricos [1000000A] | CA1 | api | ✅ passed |
| HU-G2-01 | suministro sin deudas pendientes | CA3 | api | ✅ passed |
| HU-G2-01 | CP-W01 · Ana paga su recibo de luz y ve el comprobante | CA1, CA4 | web | ✅ passed |
| HU-G2-01 | CP-W02 · Ana paga su recibo de agua | CA1, CA4 | web | ✅ passed |
| HU-G2-02 | deuda en cobranza más de 60 días no se puede pagar | CA2 | api | ✅ passed |
| HU-G2-02 | deuda id con tipo de dato inválido [{"deuda_id": "abc"}] | — | api | ✅ passed |
| HU-G2-02 | deuda id con tipo de dato inválido [{"deuda_id": null}] | — | api | ✅ passed |
| HU-G2-02 | deuda id con tipo de dato inválido [{}] | — | api | ✅ passed |
| HU-G2-02 | deuda inexistente | CA2 | api | ✅ passed |
| HU-G2-02 | deuda ya pagada no se cobra dos veces | CA2 | api | ✅ passed |
| HU-G2-02 | dos pagos simultáneos de la misma deuda solo uno es exitoso | CA3 | api | ✅ passed |
| HU-G2-02 | el comprobante de un pago de otro usuario responde 404 | CA2 | api | ✅ passed |
| HU-G2-02 | el pago genera un movimiento con el mismo código de operación | CA4 | api | ✅ passed |
| HU-G2-02 | el saldo debe cubrir el total monto  mora [saldo exacto (pasa)-120.00-201---0.00] | CA1 | api | ✅ passed |
| HU-G2-02 | el saldo debe cubrir el total monto  mora [un centimo menos (falla)-119.99-422-SALDO_INSUFICIENTE-119.99] | CA1 | api | ✅ passed |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [19 dias, bajo el tope-19-11.40-131.40] | CA1 | api | ⚠️ xfailed → [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1) |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [20 dias, justo en el tope 10 %-20-12.00-132.00] | CA1 | api | ✅ passed |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [21 dias, el tope no se supera-21-12.00-132.00] | CA1 | api | ✅ passed |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [60 dias, aun se puede pagar-60-12.00-132.00] | CA1 | api | ⚠️ xfailed → [DEF-03](defectos.md#def-03-una-deuda-con-60-días-de-atraso-se-envía-a-cobranza-y-no-se-puede-pagar) |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [el mismo dia del vencimiento-0-0.00-120.00] | CA1 | api | ⚠️ xfailed → [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1) |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [un dia antes del vencimiento--1-0.00-120.00] | CA1 | api | ✅ passed |
| HU-G2-02 | mora de 05  diario después del vencimiento con tope de 10 [un dia de atraso-1-0.60-120.60] | CA1 | api | ⚠️ xfailed → [DEF-02](defectos.md#def-02-se-cobra-mora-el-mismo-día-del-vencimiento-los-días-de-atraso-se-cuentan-con-1) |
| HU-G2-02 | pagar sin token | — | api | ✅ passed |
| HU-G2-02 | pago exitoso antes del vencimiento sin mora | CA1, CA4 | api | ✅ passed |
| HU-G2-02 | CP-W01 · Ana paga su recibo de luz y ve el comprobante | CA1, CA4 | web | ✅ passed |
| HU-G2-02 | CP-W02 · Ana paga su recibo de agua | CA1, CA4 | web | ✅ passed |
| HU-G2-03 | CP-W03 · Ana afilia un servicio de agua | CA1 | web | ✅ passed |
| HU-G2-05 | el proceso diario paga sin mora la deuda que vence hoy | CA2 | api | ✅ passed |
| HU-G2-05 | las deudas ya vencidas antes de activar el débito no se pagan automáticamente | CA4 | api | ⚠️ xfailed → [DEF-04](defectos.md#def-04-el-débito-automático-paga-deudas-que-ya-estaban-vencidas-y-sin-mora) |
| HU-G2-07 | el comprobante de un pago de otro usuario responde 404 | CA2 | api | ✅ passed |
| (sin HU) | la app responde | — | api | ✅ passed |
| (sin HU) | pagar deuda cumple el contrato openapi | — | contrato | ✅ passed |

Leyenda: ✅ pasa · ⚠️ fallo esperado: la prueba detecta un defecto ya reportado en [defectos.md](defectos.md) · ❌ falla (fallo nuevo, hay que analizarlo) · ⏭️ omitida.
