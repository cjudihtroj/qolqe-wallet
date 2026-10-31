*** Settings ***
Documentation     Caso generado con IA a partir de HU-G2-03 y revisado por el equipo.
Resource          resources/Comun.resource
Resource          pages/LoginPage.resource
Resource          pages/ServiciosPage.resource
Test Setup        Abrir Navegador Con Datos Limpios
Test Teardown     Cerrar Navegador


*** Test Cases ***
Ana afilia un servicio de agua
    [Documentation]    HU-G2-03. Generado con IA; corregido por el equipo (ver README).
    [Tags]    G2    e2e    ia    HU-G2-03    CA1    CP-W03
    Abrir Pagina De Login
    Iniciar Sesion    987654321    4826
    Deberia Estar En Inicio
    Ir A Pagar Servicios
    Select Options By    css=[data-testid="select-afiliacion-empresa"]    value    AGUA
    Fill Text    css=[data-testid="input-afiliacion-suministro"]    20000004
    Fill Text    css=[data-testid="input-afiliacion-alias"]    Agua mamá
    Click    css=[data-testid="boton-afiliar"]
    Get Text    css=[data-testid="lista-afiliaciones"]    contains    Agua mamá
    Get Text    css=[data-testid="contador-afiliaciones"]    contains    4 de 8
