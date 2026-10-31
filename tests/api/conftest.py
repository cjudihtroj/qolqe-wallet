"""QUÉ ES: los "pasos" (steps) de pytest-bdd del módulo G2. Es el puente entre el
Gherkin y la API.

CÓMO FUNCIONA: cada frase de los .feature (features/g2_*.feature) tiene aquí una
función con el mismo texto. Ej.: 'Cuando pago la deuda "ELECTRO" "10000001"' ejecuta
pagar_deuda(), que envía POST /api/servicios/pagos con httpx (TestClient) y guarda la
respuesta en ctx; luego un paso 'Entonces ...' la verifica con assert.

SECCIONES:
  - fixtures: el cliente HTTP y ctx (memoria compartida entre pasos de un escenario).
  - Dado:     preparan los datos (reiniciar, iniciar sesión, mover el reloj, fijar el saldo).
  - Cuando:   la acción que se prueba (consultar, pagar, pagos simultáneos...).
  - Entonces: las verificaciones (estado HTTP, código de error, mora, saldo...).
"""
import threading
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, then, when

from qolqe.main import app


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def ctx():
    """Memoria compartida entre los pasos de un mismo escenario."""
    return {}


def _headers(cliente, ctx):
    """Inicia sesión en cada llamada: así el token siempre es válido aunque movamos el reloj."""
    celular, pin = ctx["credenciales"]
    r = cliente.post("/api/auth/login", json={"celular": celular, "pin": pin})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _deudas(cliente, ctx, empresa, suministro):
    r = cliente.get("/api/servicios/deudas", params={"empresa": empresa, "suministro": suministro},
                    headers=_headers(cliente, ctx))
    assert r.status_code == 200, r.text
    return r.json()


def _pagar(cliente, ctx, deuda_id):
    ctx["deuda_id"] = deuda_id
    ctx["respuesta"] = cliente.post("/api/servicios/pagos", json={"deuda_id": deuda_id},
                                    headers=_headers(cliente, ctx))
    if ctx["respuesta"].status_code == 201:
        ctx["comprobante"] = ctx["respuesta"].json()
    return ctx["respuesta"]


# ---------------------------------------------------------------- Dado (precondiciones)

@given("que los datos de Qolqe están reiniciados")
def datos_reiniciados(cliente):
    # Independencia (FIRST): cada escenario parte de los mismos datos semilla y del reloj real.
    cliente.delete("/api/pruebas/reloj")
    assert cliente.post("/api/pruebas/reiniciar").status_code == 200
    yield
    cliente.delete("/api/pruebas/reloj")


@given(parsers.parse('que inicié sesión como "{celular}" con PIN "{pin}"'))
def iniciar_sesion(cliente, ctx, celular, pin):
    ctx["credenciales"] = (celular, pin)
    _headers(cliente, ctx)


@given(parsers.parse('que el reloj está {dias:d} días después del vencimiento de la deuda "{empresa}" "{suministro}"'))
def mover_reloj(cliente, ctx, dias, empresa, suministro):
    vencimiento = date.fromisoformat(_deudas(cliente, ctx, empresa, suministro)[0]["vencimiento"])
    momento = vencimiento + timedelta(days=dias)
    r = cliente.put("/api/pruebas/reloj", json={"ahora": f"{momento.isoformat()}T10:00:00"})
    assert r.status_code == 200, r.text


@given(parsers.parse('que mi saldo es "{saldo}"'))
def fijar_saldo(cliente, ctx, saldo):
    r = cliente.put("/api/pruebas/saldo", json={"celular": ctx["credenciales"][0], "saldo": saldo})
    assert r.status_code == 200, r.text


@given(parsers.parse('que pagué la deuda "{empresa}" "{suministro}"'))
def pague_deuda(cliente, ctx, empresa, suministro):
    deuda = _deudas(cliente, ctx, empresa, suministro)[0]
    assert _pagar(cliente, ctx, deuda["id"]).status_code == 201


# ---------------------------------------------------------------- Cuando (acciones)

@when(parsers.parse('consulto las deudas de la empresa "{empresa}" y suministro "{suministro}"'))
def consultar(cliente, ctx, empresa, suministro):
    ctx["respuesta"] = cliente.get("/api/servicios/deudas", params={"empresa": empresa, "suministro": suministro},
                                   headers=_headers(cliente, ctx))


@when(parsers.parse('consulto las deudas de la empresa "{empresa}" y suministro "{suministro}" sin token'))
def consultar_sin_token(cliente, ctx, empresa, suministro):
    ctx["respuesta"] = cliente.get("/api/servicios/deudas", params={"empresa": empresa, "suministro": suministro})


@when(parsers.parse('pago la deuda "{empresa}" "{suministro}"'))
def pagar_deuda(cliente, ctx, empresa, suministro):
    ctx["saldo_inicial"] = _saldo(cliente, ctx)
    _pagar(cliente, ctx, _deudas(cliente, ctx, empresa, suministro)[0]["id"])


@when(parsers.parse("pago la deuda con id {deuda_id:d}"))
def pagar_por_id(cliente, ctx, deuda_id):
    _pagar(cliente, ctx, deuda_id)


@when(parsers.parse("pago la deuda con id {deuda_id:d} sin token"))
def pagar_sin_token(cliente, ctx, deuda_id):
    ctx["respuesta"] = cliente.post("/api/servicios/pagos", json={"deuda_id": deuda_id})


@when("pago otra vez la misma deuda")
def pagar_otra_vez(cliente, ctx):
    _pagar(cliente, ctx, ctx["deuda_id"])


@when(parsers.parse("envío el cuerpo de pago {cuerpo}"))
def enviar_cuerpo(cliente, ctx, cuerpo):
    ctx["respuesta"] = cliente.post("/api/servicios/pagos", content=cuerpo,
                                    headers={**_headers(cliente, ctx), "Content-Type": "application/json"})


@when(parsers.parse('envío {n:d} pagos simultáneos de la deuda "{empresa}" "{suministro}"'))
def pagos_simultaneos(ctx, cliente, n, empresa, suministro):
    deuda_id = _deudas(cliente, ctx, empresa, suministro)[0]["id"]
    headers = [_headers(cliente, ctx) for _ in range(n)]
    barrera, estados = threading.Barrier(n), []

    def pagar(h):
        barrera.wait()  # todos salen al mismo tiempo
        estados.append(TestClient(app).post("/api/servicios/pagos", json={"deuda_id": deuda_id}, headers=h).status_code)

    hilos = [threading.Thread(target=pagar, args=(h,)) for h in headers]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    ctx["estados"] = estados


@when("consulto el comprobante de ese pago")
def consultar_comprobante(cliente, ctx):
    codigo = ctx["comprobante"]["codigo_operacion"]
    ctx["respuesta"] = cliente.get(f"/api/servicios/pagos/{codigo}", headers=_headers(cliente, ctx))


# ---------------------------------------------------------------- Entonces (verificaciones)

@then(parsers.parse('la respuesta tiene estado {estado:d} y código "{codigo}"'))
def verificar_estado_y_codigo(ctx, estado, codigo):
    r = ctx["respuesta"]
    assert r.status_code == estado, f"Esperado {estado}, obtenido {r.status_code}: {r.text}"
    if codigo != "-":
        assert r.json()["codigo"] == codigo, r.text


@then(parsers.parse("la respuesta tiene estado {estado:d}"))
def verificar_estado(ctx, estado):
    r = ctx["respuesta"]
    assert r.status_code == estado, f"Esperado {estado}, obtenido {r.status_code}: {r.text}"


@then(parsers.parse("recibo {n:d} deudas ordenadas por vencimiento ascendente"))
def verificar_orden(ctx, n):
    deudas = ctx["respuesta"].json()
    assert len(deudas) == n
    vencimientos = [d["vencimiento"] for d in deudas]
    assert vencimientos == sorted(vencimientos)


@then(parsers.parse('cada deuda tiene los campos "{campos}"'))
def verificar_campos_deuda(ctx, campos):
    for deuda in ctx["respuesta"].json():
        for campo in campos.split(", "):
            assert campo in deuda, f"Falta el campo {campo}"


@then(parsers.parse('el titular de cada deuda está enmascarado como "{titular}"'))
def verificar_titular(ctx, titular):
    assert all(d["titular"] == titular for d in ctx["respuesta"].json())


@then(parsers.parse('la deuda tiene estado "{estado}"'))
def verificar_estado_deuda(ctx, estado):
    deuda = ctx["respuesta"].json()[0]
    assert deuda["estado"] == estado, f"Esperado estado {estado}, obtenido {deuda['estado']} (días de atraso {deuda['dias_atraso']})"


@then(parsers.parse("la deuda tiene {dias:d} días de atraso"))
def verificar_atraso(ctx, dias):
    deuda = ctx["respuesta"].json()[0]
    assert deuda["dias_atraso"] == dias, f"Esperado {dias} días de atraso, obtenido {deuda['dias_atraso']} (mora {deuda['mora']})"


@then(parsers.parse('el comprobante muestra monto "{monto}", mora "{mora}" y total "{total}"'))
def verificar_comprobante(ctx, monto, mora, total):
    c = ctx["respuesta"].json()
    assert (c["monto"], c["mora"], c["total"]) == (monto, mora, total), (
        f"Esperado mora {mora} y total {total}, obtenido mora {c['mora']} y total {c['total']}")


@then(parsers.parse('el comprobante tiene los campos "{campos}"'))
def verificar_campos_comprobante(ctx, campos):
    c = ctx["respuesta"].json()
    for campo in campos.split(", "):
        assert c.get(campo), f"Falta el campo {campo}"


def _saldo(cliente, ctx):
    return cliente.get("/api/cuentas/me/saldo", headers=_headers(cliente, ctx)).json()["saldo"]


@then(parsers.parse('mi saldo es "{saldo}"'))
def verificar_saldo(cliente, ctx, saldo):
    assert _saldo(cliente, ctx) == saldo


@then(parsers.parse("solo {n:d} pago es exitoso y el otro responde 409"))
def verificar_concurrencia(ctx, n):
    assert sorted(ctx["estados"]) == [201] * n + [409] * (len(ctx["estados"]) - n), ctx["estados"]


@then("existe un movimiento con el código de operación del comprobante")
def verificar_movimiento(cliente, ctx):
    codigo = ctx["comprobante"]["codigo_operacion"]
    r = cliente.get(f"/api/movimientos/{codigo}", headers=_headers(cliente, ctx))
    assert r.status_code == 200, r.text
    assert r.json()["codigo_operacion"] == codigo


# ---------------------------------------------------------------- débito automático (HU-G2-05, extra)

@given(parsers.parse('que afilié "{empresa}" "{suministro}" con alias "{alias}" y débito automático activo'))
def afiliar_con_debito(cliente, ctx, empresa, suministro, alias):
    h = _headers(cliente, ctx)
    r = cliente.post("/api/servicios/afiliaciones", json={"empresa": empresa, "suministro": suministro, "alias": alias},
                     headers=h)
    assert r.status_code == 201, r.text
    r = cliente.put(f"/api/servicios/afiliaciones/{r.json()['id']}", json={"debito_automatico": True}, headers=h)
    assert r.json()["debito_automatico"] is True


@when("se ejecuta el proceso diario")
def proceso_diario(cliente):
    assert cliente.post("/api/pruebas/procesar-diario").status_code == 200


def _pagos_debito(cliente, ctx, empresa, suministro):
    pagos = cliente.get("/api/servicios/pagos", headers=_headers(cliente, ctx)).json()
    return [p for p in pagos if p["origen"] == "DEBITO_AUTOMATICO"
            and (p["empresa"], p["suministro"]) == (empresa, suministro)]


@then(parsers.parse('se registró {n:d} pago por débito automático de "{empresa}" "{suministro}" con mora "{mora}"'))
def verificar_un_debito(cliente, ctx, n, empresa, suministro, mora):
    pagos = _pagos_debito(cliente, ctx, empresa, suministro)
    assert len(pagos) == n and all(p["mora"] == mora for p in pagos), pagos


@then(parsers.parse('se registraron {n:d} pagos por débito automático de "{empresa}" "{suministro}"'))
def verificar_debitos(cliente, ctx, n, empresa, suministro):
    pagos = _pagos_debito(cliente, ctx, empresa, suministro)
    assert len(pagos) == n, f"Esperado {n} pagos por débito automático, obtenido {len(pagos)}: " + ", ".join(
        f"{p['periodo']} total {p['total']} mora {p['mora']}" for p in pagos)
