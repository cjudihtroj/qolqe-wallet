*** Settings ***
Documentation     G2 · Pago de servicios — happy path E2E por la interfaz web.
...               HU-G2-01 (consultar deuda) + HU-G2-02 (pagar deuda).
...               Patrón: Page Object (carpeta pages/) + Fixtures (Setup/Teardown).
Resource          resources/Comun.resource
Resource          pages/LoginPage.resource
Resource          pages/ServiciosPage.resource
Test Setup        Abrir Navegador Con Datos Limpios
Test Teardown     Cerrar Navegador


*** Variables ***
# Datos semilla de Qolqe (README, sección 4)
${CELULAR_ANA}    987654321
${PIN_ANA}        4826


*** Test Cases ***
Ana paga su recibo de luz y ve el comprobante
    [Documentation]    Deuda ELECTRO 10000001: S/ 120.00, vence en 10 días (sin mora).
    ...                Saldo inicial de Ana: S/ 1,500.00 → saldo final: S/ 1,380.00
    [Tags]    G2    e2e    happy-path    HU-G2-01    HU-G2-02    CA1    CA4    CP-W01
    Given Ana ha iniciado sesion
    When consulta la deuda del suministro    ELECTRO    10000001
    And paga la deuda por un total de    S/ 120.00
    Then el comprobante muestra el pago    ELECTRO    10000001    S/ 120.00    S/ 1,380.00


*** Keywords ***
# Pasos estilo BDD (Given/When/Then). Cada paso llama a un Page Object.
Ana ha iniciado sesion
    Abrir Pagina De Login
    Iniciar Sesion    ${CELULAR_ANA}    ${PIN_ANA}
    Deberia Estar En Inicio

consulta la deuda del suministro
    [Arguments]    ${empresa}    ${suministro}
    Ir A Pagar Servicios
    Consultar Deuda    ${empresa}    ${suministro}

paga la deuda por un total de
    [Arguments]    ${total}
    Pagar Primera Deuda    ${total}

el comprobante muestra el pago
    [Arguments]    ${empresa}    ${suministro}    ${total}    ${saldo}
    El Comprobante Deberia Mostrar    ${empresa}    ${suministro}    ${total}    ${saldo}
