"""QUÉ ES: el archivo que pytest encuentra y ejecuta (empieza con test_).

PARA QUÉ: con scenarios() convierte CADA escenario de los 3 archivos .feature en una
prueba de pytest. Es corto porque la lógica está en tests/api/conftest.py (los pasos)
y los casos están en features/ (el Gherkin).
"""
from pytest_bdd import scenarios

scenarios("g2_consultar_deudas.feature", "g2_pagar_deuda.feature", "g2_debito_automatico.feature")
