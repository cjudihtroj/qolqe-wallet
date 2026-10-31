*** Settings ***
Documentation     PAGE OBJECT de la pantalla /login.
...               Aquí viven los LOCALIZADORES (cómo encontrar cada elemento)
...               y las ACCIONES (qué puede hacer el usuario).
...               Si la pantalla cambia, solo se corrige ESTE archivo.
Library           Browser


*** Variables ***
# Localizadores: usamos data-testid (atributo pensado para pruebas, estable)
${LOGIN_CELULAR}      css=[data-testid="input-celular"]
${LOGIN_PIN}          css=[data-testid="input-pin"]
${LOGIN_BOTON}        css=[data-testid="boton-ingresar"]
${INICIO_SALDO}       css=[data-testid="saldo-valor"]


*** Keywords ***
Abrir Pagina De Login
    Go To    ${URL}/login

Iniciar Sesion
    [Documentation]    Llena celular y PIN, y pulsa "Ingresar".
    [Arguments]    ${celular}    ${pin}
    Fill Text      ${LOGIN_CELULAR}    ${celular}
    Fill Secret    ${LOGIN_PIN}        $pin
    Click          ${LOGIN_BOTON}

Deberia Estar En Inicio
    [Documentation]    Las aserciones de Browser REINTENTAN solas hasta el timeout (espera automática).
    Get Url    contains    /inicio
    Get Text    ${INICIO_SALDO}    contains    S/
