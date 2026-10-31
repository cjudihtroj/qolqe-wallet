*** Settings ***
Documentation     Caso generado EN VIVO con IA (Claude Code + rf-mcp) y revisado por el equipo.
...               La IA ejecutó cada paso en un navegador real y luego generó el .robot;
...               lo refactorizamos para reutilizar los Page Objects y los fixtures (ver IA.md).
Resource          resources/Comun.resource
Resource          pages/LoginPage.resource
Resource          pages/ServiciosPage.resource
Test Setup        Abrir Navegador Con Datos Limpios
Test Teardown     Cerrar Navegador


*** Test Cases ***
Ana paga su recibo de agua
    [Documentation]    Deuda AGUA 2000000008: S/ 45.00, vence en 3 días.
    ...                Saldo inicial de Ana: S/ 1,500.00 → saldo final: S/ 1,455.00
    [Tags]    G2    e2e    ia    HU-G2-01    HU-G2-02    CA1    CA4    CP-W02
    Abrir Pagina De Login
    Iniciar Sesion    987654321    4826
    Deberia Estar En Inicio
    Ir A Pagar Servicios
    Consultar Deuda    AGUA    2000000008
    Pagar Primera Deuda    S/ 45.00
    El Comprobante Deberia Mostrar    AGUA    2000000008    S/ 45.00    S/ 1,455.00
