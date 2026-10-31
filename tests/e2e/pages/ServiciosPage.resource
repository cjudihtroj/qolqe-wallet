*** Settings ***
Documentation     PAGE OBJECT de la pantalla /servicios (módulo G2: pago de servicios).
Library           Browser


*** Variables ***
${SERV_EMPRESA}             css=[data-testid="select-empresa"]
${SERV_SUMINISTRO}          css=[data-testid="input-suministro"]
${SERV_BOTON_CONSULTAR}     css=[data-testid="boton-consultar"]
${SERV_DEUDA}               css=[data-testid="deuda"]
${SERV_BOTON_PAGAR}         css=[data-testid="boton-pagar-deuda"]
${SERV_DIALOGO}             css=[data-testid="dialogo-pago"]
${SERV_DIALOGO_TOTAL}       css=[data-testid="pago-total"]
${SERV_BOTON_CONFIRMAR}     css=[data-testid="boton-confirmar-pago"]
${SERV_COMPROBANTE}         css=[data-testid="comprobante"]
${COMP_CODIGO}              css=[data-testid="comprobante-codigo"]
${COMP_EMPRESA}             css=[data-testid="comprobante-empresa"]
${COMP_SUMINISTRO}          css=[data-testid="comprobante-suministro"]
${COMP_TOTAL}               css=[data-testid="comprobante-total"]
${COMP_SALDO}               css=[data-testid="comprobante-saldo"]


*** Keywords ***
Ir A Pagar Servicios
    Click    css=[data-testid="nav-servicios"]
    Get Url    contains    /servicios
    # Esperar a que la pantalla TERMINE de cargar (sus datos llegan por API).
    # Sin esto la prueba era frágil: escribía antes de que la página estuviera lista.
    Get Text    css=[data-testid="contador-afiliaciones"]    contains    de 8

Consultar Deuda
    [Documentation]    Elige la empresa, escribe el suministro y consulta.
    [Arguments]    ${empresa}    ${suministro}
    Select Options By    ${SERV_EMPRESA}    value    ${empresa}
    Fill Text            ${SERV_SUMINISTRO}    ${suministro}
    Click                ${SERV_BOTON_CONSULTAR}
    # Espera por CONDICIÓN (no sleep): que aparezca al menos una deuda
    Wait For Elements State    ${SERV_DEUDA} >> nth=0    visible

Pagar Primera Deuda
    [Documentation]    Pulsa "Pagar" en la primera deuda y confirma en el diálogo.
    [Arguments]    ${total_esperado}
    Click    ${SERV_DEUDA} >> nth=0 >> ${SERV_BOTON_PAGAR}
    Wait For Elements State    ${SERV_DIALOGO}    visible
    Get Text    ${SERV_DIALOGO_TOTAL}    ==    ${total_esperado}
    Click    ${SERV_BOTON_CONFIRMAR}

El Comprobante Deberia Mostrar
    [Documentation]    Verifica el comprobante (HU-G2-02, CA4).
    [Arguments]    ${empresa}    ${suministro}    ${total}    ${saldo}
    Wait For Elements State    ${SERV_COMPROBANTE}    visible
    Get Text    ${COMP_CODIGO}        !=    ${EMPTY}
    Get Text    ${COMP_EMPRESA}       ==    ${empresa}
    Get Text    ${COMP_SUMINISTRO}    ==    ${suministro}
    Get Text    ${COMP_TOTAL}         ==    ${total}
    Get Text    ${COMP_SALDO}         ==    ${saldo}
