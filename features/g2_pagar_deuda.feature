# language: es
# ─────────────────────────────────────────────────────────────────────────
# QUÉ ES: escenarios de prueba en Gherkin (lenguaje natural) de HU-G2-02 (pagar una deuda).
# PARA QUÉ: verificar el pago: cálculo de mora, saldo suficiente, deuda ya pagada o en
#   cobranza, pagos simultáneos, comprobante, movimiento y seguridad.
# CÓMO SE USA: no se ejecuta solo. pytest-bdd lee este archivo y conecta cada
#   frase (Dado/Cuando/Entonces) con una función de tests/api/conftest.py.
#   Ejecutar: pytest -v   ·   solo esta HU: pytest -v -m "HU-G2-02"
# ETIQUETAS (@...): trazabilidad HU → criterio de aceptación (CA) → técnica.
# ─────────────────────────────────────────────────────────────────────────
@G2 @HU-G2-02
Característica: HU-G2-02 Pagar una deuda (Prioridad Alta)
  Como cliente
  quiero pagar la deuda de un servicio con mi saldo
  para no acudir a una agencia

  Antecedentes:
    Dado que los datos de Qolqe están reiniciados
    Y que inicié sesión como "987654321" con PIN "4826"

  @CA1 @CA4 @camino-feliz
  Escenario: Pago exitoso antes del vencimiento, sin mora
    Cuando pago la deuda "ELECTRO" "10000001"
    Entonces la respuesta tiene estado 201
    Y el comprobante muestra monto "120.00", mora "0.00" y total "120.00"
    Y el comprobante tiene los campos "codigo_operacion, empresa, suministro, periodo, monto, mora, total, saldo"
    Y mi saldo es "1380.00"

  @CA1 @R-G2-03 @valor-limite
  Esquema del escenario: Mora de 0.5 % diario después del vencimiento, con tope de 10 %
    Dado que el reloj está <dias> días después del vencimiento de la deuda "ELECTRO" "10000001"
    Cuando pago la deuda "ELECTRO" "10000001"
    Entonces la respuesta tiene estado 201
    Y el comprobante muestra monto "120.00", mora "<mora>" y total "<total>"

    Ejemplos:
      | caso                           | dias | mora  | total  |
      | un dia antes del vencimiento   | -1   | 0.00  | 120.00 |
      | el mismo dia del vencimiento   | 0    | 0.00  | 120.00 |
      | un dia de atraso               | 1    | 0.60  | 120.60 |
      | 19 dias, bajo el tope          | 19   | 11.40 | 131.40 |
      | 20 dias, justo en el tope 10 % | 20   | 12.00 | 132.00 |
      | 21 dias, el tope no se supera  | 21   | 12.00 | 132.00 |
      | 60 dias, aun se puede pagar    | 60   | 12.00 | 132.00 |

  @CA1 @RN-08 @valor-limite
  Esquema del escenario: El saldo debe cubrir el total (monto + mora)
    Dado que mi saldo es "<saldo>"
    Cuando pago la deuda "ELECTRO" "10000001"
    Entonces la respuesta tiene estado <estado> y código "<codigo>"
    Y mi saldo es "<saldo_final>"

    Ejemplos:
      | caso                     | saldo  | estado | codigo             | saldo_final |
      | un centimo menos (falla) | 119.99 | 422    | SALDO_INSUFICIENTE | 119.99      |
      | saldo exacto (pasa)      | 120.00 | 201    | -                  | 0.00        |

  @CA2
  Escenario: Deuda inexistente
    Cuando pago la deuda con id 999999
    Entonces la respuesta tiene estado 404 y código "DEUDA_NO_ENCONTRADA"

  @CA2 @efecto
  Escenario: Deuda ya pagada no se cobra dos veces
    Dado que pagué la deuda "ELECTRO" "10000001"
    Cuando pago otra vez la misma deuda
    Entonces la respuesta tiene estado 409 y código "DEUDA_YA_PAGADA"
    Y mi saldo es "1380.00"

  @CA2 @R-G2-04 @efecto
  Escenario: Deuda en cobranza (más de 60 días) no se puede pagar
    Dado que el reloj está 61 días después del vencimiento de la deuda "ELECTRO" "10000001"
    Cuando pago la deuda "ELECTRO" "10000001"
    Entonces la respuesta tiene estado 422 y código "DEUDA_EN_COBRANZA"
    Y mi saldo es "1500.00"

  @CA3 @concurrencia
  Escenario: Dos pagos simultáneos de la misma deuda, solo uno es exitoso
    Cuando envío 2 pagos simultáneos de la deuda "ELECTRO" "10000001"
    Entonces solo 1 pago es exitoso y el otro responde 409
    Y mi saldo es "1380.00"

  @CA4 @RN-10 @efecto
  Escenario: El pago genera un movimiento con el mismo código de operación
    Cuando pago la deuda "ELECTRO" "10000001"
    Entonces la respuesta tiene estado 201
    Y existe un movimiento con el código de operación del comprobante

  @HU-G2-07 @CA2 @seguridad
  Escenario: El comprobante de un pago de otro usuario responde 404
    Dado que pagué la deuda "ELECTRO" "10000001"
    Y que inicié sesión como "912345678" con PIN "7391"
    Cuando consulto el comprobante de ese pago
    Entonces la respuesta tiene estado 404 y código "PAGO_NO_ENCONTRADO"

  @seguridad
  Escenario: Pagar sin token
    Cuando pago la deuda con id 1 sin token
    Entonces la respuesta tiene estado 401 y código "NO_AUTENTICADO"

  @tecnico @particion
  Esquema del escenario: deuda_id con tipo de dato inválido
    Cuando envío el cuerpo de pago <cuerpo>
    Entonces la respuesta tiene estado 422 y código "SOLICITUD_INVALIDA"

    Ejemplos:
      | cuerpo                |
      | {}                    |
      | {"deuda_id": "abc"}   |
      | {"deuda_id": null}    |
