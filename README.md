# Qolqe Wallet

Billetera digital **ficticia** usada como sistema bajo prueba (SUT) en el Proyecto 2 del curso **CS5383 Pruebas y Verificación de Software**.

> ⚠️ **Antes de empezar:**
> - **No modifiquen el código de la carpeta `qolqe/`.** Su trabajo es probarlo, no repararlo.
> - Todos los datos son ficticios.

---

## 1. Requisitos

- Python **3.11 o superior** (recomendado 3.12)
- Git

## 2. Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn qolqe.main:app --reload
```

| Recurso | URL |
|---|---|
| Interfaz web | http://localhost:8000 |
| Documentación de la API (Swagger / OpenAPI) | http://localhost:8000/docs |
| Contrato OpenAPI en JSON | http://localhost:8000/openapi.json |
| Estado del servicio | http://localhost:8000/api/salud |

La primera vez la app crea la base de datos en `datos/` (tarda unos segundos porque genera los usuarios de carga). Para empezar desde cero, borren la carpeta `datos/` o usen `POST /api/pruebas/reiniciar`.

> Ejecuten **un solo proceso** de uvicorn (sin `--workers`). El reloj de pruebas vive en memoria.

### Variables de entorno (opcionales)

| Variable | Por defecto | Uso |
|---|---|---|
| `QOLQE_BD` | `datos/qolqe.db` | Ruta de la base de datos |
| `QOLQE_MODO_PRUEBA` | `1` | `1` habilita la API de soporte para pruebas (`/api/pruebas/*`) |
| `QOLQE_MINUTOS_TOKEN` | `30` | Vigencia del token JWT |
| `QOLQE_CLAVE_SECRETA` | clave de desarrollo | Firma de los tokens |

---

## 3. Funcionalidades

| Módulo | Pantalla | Endpoints principales |
|---|---|---|
| **Núcleo:** registro, sesión, perfil, saldo y transferencias | `/registro`, `/login`, `/inicio`, `/perfil`, `/transferir` | `POST /api/usuarios` · `POST /api/auth/login` · `POST /api/auth/logout` · `GET/PUT /api/cuentas/me` · `POST /api/cuentas/me/cierre` · `GET /api/cuentas/me/saldo` · `POST /api/transferencias` · `GET /api/transferencias/comision` |
| **G1** Recargas y recargas programadas | `/recargas` | `GET /api/recargas/configuracion` · `GET/POST /api/recargas` · `GET/POST /api/recargas/programadas` · `PUT/DELETE /api/recargas/programadas/{id}` · `POST /api/recargas/programadas/{id}/pausar` · `POST .../reanudar` |
| **G2** Pago de servicios y afiliaciones | `/servicios` | `GET /api/servicios/empresas` · `GET /api/servicios/deudas` · `GET/POST /api/servicios/pagos` · `GET /api/servicios/pagos/{codigo}` · `GET/POST /api/servicios/afiliaciones` · `PUT/DELETE /api/servicios/afiliaciones/{id}` |
| **G3** Historial y categorías | `/historial` | `GET /api/movimientos` · `GET /api/movimientos/recientes` · `GET /api/movimientos/{codigo}` · `PUT /api/movimientos/{codigo}/clasificacion` · `GET /api/movimientos/exportar` · `GET/POST /api/categorias` · `PUT/DELETE /api/categorias/{id}` |
| **G4** Contactos y solicitudes de dinero | `/contactos`, `/solicitudes` | `GET/POST /api/contactos` · `PUT/DELETE /api/contactos/{id}` · `GET/POST /api/solicitudes` · `POST /api/solicitudes/{id}/aceptar` · `.../rechazar` · `.../cancelar` |
| **G5** Límites y alertas de consumo | `/limites` | `GET/PUT /api/limites` · `GET/POST /api/limites/alertas` · `PUT/DELETE /api/limites/alertas/{id}` |
| **G6** Seguridad, dispositivos y sesiones | `/seguridad`, `/desbloqueo` | `PUT /api/seguridad/pin` · `POST /api/seguridad/desbloqueo/solicitar` · `.../confirmar` · `GET/POST /api/seguridad/dispositivos` · `PUT/DELETE /api/seguridad/dispositivos/{id}` · `GET/DELETE /api/seguridad/sesiones` · `DELETE /api/seguridad/sesiones/{id}` |

Las **historias de usuario, criterios de aceptación y reglas de negocio** están en `docs/requisitos.md`. Las funciones que las implementan, sin base de datos ni red, están en `qolqe/reglas/`:

```
qolqe/reglas/nucleo.py      qolqe/reglas/servicios.py   qolqe/reglas/contactos.py
qolqe/reglas/recargas.py    qolqe/reglas/historial.py   qolqe/reglas/limites.py
qolqe/reglas/seguridad.py
```

### Autenticación

```http
POST /api/auth/login
Content-Type: application/json

{"celular": "987654321", "pin": "4826"}
```

Opcionalmente se envía `"dispositivo_id"` (identificador de un dispositivo de confianza, ver G6). La respuesta incluye `access_token` y `sesion_id`. Envíen el token en cada solicitud protegida:

```http
Authorization: Bearer <access_token>
```

- Cada inicio de sesión crea una **sesión**; el token vence a los **30 minutos**.
- `POST /api/auth/logout` cierra la sesión. Las sesiones activas se consultan y cierran en `/api/seguridad/sesiones`.
- Tras **3 intentos fallidos** consecutivos, la cuenta se bloquea 15 minutos (`423`).

### Convenciones de la API

- **Montos:** se envían como número o texto decimal (`100`, `"100.50"`) y se devuelven como texto con 2 decimales (`"100.50"`).
- **Fechas:** hora de Lima, formato `AAAA-MM-DDTHH:MM:SS`.
- **Errores:** todos responden con un código estable y un mensaje:

```json
{"codigo": "SALDO_INSUFICIENTE", "detail": "Saldo insuficiente para realizar la operación"}
```

| HTTP | Significado | Ejemplos de `codigo` |
|---|---|---|
| 204 | Eliminación o cierre correcto, sin contenido | |
| 401 | Sin token, token inválido, vencido o de una sesión cerrada, o credenciales incorrectas | `NO_AUTENTICADO`, `CREDENCIALES_INVALIDAS`, `CUENTA_CERRADA` |
| 404 | Recurso inexistente **o de otro usuario** | `DESTINO_NO_REGISTRADO`, `CONTACTO_NO_ENCONTRADO`, `SIN_DEUDA_PENDIENTE` |
| 409 | Conflicto con el estado actual | `CELULAR_REGISTRADO`, `ALIAS_DUPLICADO`, `DEUDA_YA_PAGADA`, `ESTADO_INVALIDO` |
| 422 | Regla de negocio o datos inválidos | `MONTO_INVALIDO`, `SALDO_INSUFICIENTE`, `LIMITE_DIARIO_EXCEDIDO`, `FILTRO_INVALIDO`, `SOLICITUD_INVALIDA` |
| 423 | Cuenta bloqueada | `CUENTA_BLOQUEADA` |

El contrato completo está en `/docs` (Swagger) y en `/openapi.json`. Cada operación indica su historia de usuario, los esquemas de entrada y salida con sus restricciones, y todos los códigos de error que puede devolver, con un ejemplo por código.

---

## 4. Datos de prueba

Se restauran con `POST /api/pruebas/reiniciar`. Las fechas de las deudas y algunos movimientos se calculan **respecto del día actual** del reloj de la app.

### Usuarios

| Usuario | Celular | PIN | Correo | Saldo | Notas |
|---|---|---|---|---|---|
| Ana Torres Quispe | 987654321 | 4826 | ana.torres@correo.pe | S/ 1,500.00 | Usuario principal de ejemplo (ver abajo). Ha usado otros PIN antes |
| Bruno Díaz Mendoza | 912345678 | 7391 | bruno.diaz@correo.pe | S/ 800.00 | Tiene a Ana como contacto |
| Carla Ramos Huamán | 956781234 | 5917 | carla.ramos@correo.pe | S/ 50.00 | Saldo bajo. Tiene a Ana como contacto |
| Diego Salas Paredes | 998877665 | 3604 | diego.salas@correo.pe | S/ 2,500.00 | Límite diario configurado en S/ 1,000. Tiene a Fabián como contacto |
| Elena Vargas Ccori | 923456789 | 8152 | elena.vargas@correo.pe | S/ 300.00 | **Cuenta bloqueada** al reiniciar (para probar el desbloqueo) |
| Fabián Rojas Núñez | 934567812 | 6029 | fabian.rojas@correo.pe | S/ 0.00 | **Cuenta cerrada** |

### Datos de Ana por módulo

| Módulo | Datos |
|---|---|
| G1 | Programada "Mamá" (987111222, S/ 20, día 15, ACTIVA) y "Trabajo" (999000111, S/ 10, día 5, PAUSADA). Una recarga de hoy al 999000111 |
| G2 | Afiliaciones "Luz casa" (ELECTRO 10000001), "Agua depa" (AGUA 2000000008, **débito automático activo**) e "Internet casa" (INTERNET 300000000007) |
| G3 | Historial de unos 60 días. Categorías Comida, Familia y Servicios, con movimientos asignados y una nota |
| G4 | Contactos "Bruno" (favorito) y "Prima Carla". Solicitudes: Bruno le pide S/ 45.00 (pendiente), Carla le pidió S/ 30.00 hace más de 48 horas, y Ana le pide S/ 20.00 a Bruno (pendiente) |
| G5 | Alerta de TRANSFERENCIAS con umbral S/ 300 |
| G6 | Dispositivo de confianza "Celular de Ana" con identificador `a1b2c3d4e5f60718` |

### Usuarios de carga (pruebas de rendimiento)

- Celulares **900000001** a **900000200**, todos con PIN **2580**.
- Saldo S/ 10,000.00 y unos 1,000 movimientos de los últimos 120 días cada uno.

### Deudas de servicios

| Empresa | Suministro | Vencimiento (respecto de hoy) |
|---|---|---|
| ELECTRO | 10000001 | Vence en 10 días |
| ELECTRO | 10000002 | Vence hoy |
| ELECTRO | 10000003 | Venció ayer |
| ELECTRO | 100000009 | Dos periodos: uno venció hace 5 días y otro vence en 25 |
| AGUA | 20000004 | Venció hace 10 días |
| AGUA | 20000005 | Venció hace 30 días |
| AGUA | 2000000008 | Vence en 3 días |
| INTERNET | 300000000006 | Venció hace 60 días |
| INTERNET | 300000000007 | Venció hace 61 días |
| AGUA | 4000000001 a 4000000200 | Venció hace 5 días (para pruebas de carga) |

### Transferencias interbancarias

Usen cualquier CCI de 20 dígitos, por ejemplo `00219300123456789012`.

---

## 5. API de soporte para pruebas

Disponible solo con `QOLQE_MODO_PRUEBA=1`. **No forma parte del producto**: existe para que las pruebas automatizadas sean repetibles.

| Endpoint | Para qué |
|---|---|
| `POST /api/pruebas/reiniciar` | Restaura todos los datos semilla |
| `GET /api/pruebas/reloj` | Ver la fecha y hora de la app |
| `PUT /api/pruebas/reloj` | Fijar (`{"ahora": "2026-11-15T10:00:00"}`) o adelantar (`{"avanzar_minutos": 60}`) el reloj |
| `DELETE /api/pruebas/reloj` | Volver a la hora real |
| `GET /api/pruebas/notificaciones?celular=...` | Ver los SMS simulados enviados a un celular (por ejemplo, el código de desbloqueo) |
| `PUT /api/pruebas/saldo` | Fijar el saldo de un usuario: `{"celular": "...", "saldo": "100.00"}` |
| `POST /api/pruebas/procesar-diario` | Ejecutar el proceso diario (recargas programadas y débitos automáticos) con la fecha del reloj de la app |

> 💡 Para probar el proceso diario: fijen o adelanten el reloj al día que necesiten y luego llamen a `POST /api/pruebas/procesar-diario`.
>
> 💡 Si sus pruebas modifican datos (transferencias, bloqueos, límites), reinicien los datos antes de cada prueba o diseñen datos independientes. Así cumplen la propiedad *Independent* de FIRST.

---

## 6. Estructura sugerida del repositorio del grupo

```
qolqe/                    # App (NO modificar)
features/                 # Casos del módulo en Gherkin
tests/
  api/                    # Parte 1
  e2e/pages/              # Parte 2 (Page Objects)
  performance/            # Parte 3
docs/                     # Herramienta, trazabilidad, rendimiento, defectos
.github/workflows/        # Pipeline (Parte 2)
IA.md                     # Declaración de uso de IA
```

En `docs/` encontrarán la especificación de requisitos, la plantilla del informe del proyecto y la plantilla del reporte de defectos; en la raíz, la plantilla de `IA.md`.

---

## 7. Pruebas del módulo G2 · Pago de servicios (Entrega 1)

Pruebas de API automatizadas del módulo **G2**, con foco en las HU de prioridad **Alta**: **HU-G2-01 Consultar deudas** y **HU-G2-02 Pagar una deuda**. Además, como extra, HU-G2-05 (débito automático) y HU-G2-07 CA2 (comprobante de otro usuario).

| Tipo | Herramienta | De dónde salen los casos |
|---|---|---|
| **Funcional** | pytest + **pytest-bdd** + httpx (TestClient) | Escenarios Gherkin en español (`features/*.feature`) escritos a partir de las HU, con partición de equivalencia y valores límite |
| **Técnica** | **Schemathesis** (dentro de pytest) | Se generan automáticamente desde el contrato OpenAPI (`/openapi.json`) de `POST /api/servicios/pagos` |

### 7.1 Instalación y ejecución

```bash
python -m venv .venv
.venv\Scripts\activate              # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                              # corre TODO: funcional + técnico + resúmenes
```

No hace falta levantar la app: las pruebas funcionales usan TestClient y la prueba técnica levanta Qolqe sola en un puerto libre. Las pruebas usan su propia base de datos (`datos/pruebas.db`), así que no tocan la de la demo. Una ejecución completa tarda unos 45 segundos.

| Comando | Qué ejecuta |
|---|---|
| `pytest` | Todo, y al final los dos resúmenes en la terminal |
| `pytest -v` | Igual, pero con una línea por caso |
| `pytest -v -m "HU-G2-02"` | Solo **Pagar una deuda**. Sirve cualquier etiqueta del `.feature`: `HU-G2-01`, `HU-G2-05`, `CA1`, `valor-limite`, `seguridad`… |
| `pytest -m schemathesis` | Solo la prueba técnica desde el contrato |
| `pytest --html=reportes/pytest/reporte.html --self-contained-html` | Todo, más el reporte HTML funcional |
| `$env:SCHEMATHESIS_MODO="aleatorio"; pytest -m schemathesis` | Prueba técnica con casos nuevos al azar. Por defecto es **determinista**: los mismos casos en cada ejecución |

### 7.2 Resúmenes automáticos en la terminal

Cada `pytest` calcula los resúmenes con los resultados de **esa** ejecución (lo hace `tests/conftest.py`):

- **RESUMEN FUNCIONAL:** casos, pasan y fallan por **historia de usuario** y por **técnica**. Luego, cada fallo con su mensaje *esperado vs. obtenido* y el **defecto** al que corresponde (DEF-01 a DEF-04). Un fallo que no corresponda a un defecto ya conocido aparece como **`NUEVO, analizar`**: eso indica una regresión o un defecto nuevo.
- **RESUMEN TÉCNICO:** número de casos generados por Schemathesis, errores 500 y una tabla por **validación de entrada** con cuántos casos hubo, si la API respondió bien y en qué filas del reporte están.

### 7.3 Reportes

| Reporte | Cómo se genera | Cómo se abre |
|---|---|---|
| Funcional (pytest-html) | `pytest --html=reportes/pytest/reporte.html --self-contained-html` | `start reportes\pytest\reporte.html` |
| Funcional, solo pagar deuda | `pytest -m "HU-G2-02" --html=reportes/pytest/hu-g2-02.html --self-contained-html` | `start reportes\pytest\hu-g2-02.html` |
| Técnico (Schemathesis) | Automático en cada `pytest` o `pytest -m schemathesis` | `start reportes\schemathesis\ultimo\reporte.html` |

`reportes/` está en `.gitignore`: es evidencia local y se regenera en cada ejecución. El reporte técnico incluye la tabla *"Dónde está cada validación de entrada"* y el detalle de cada caso: cuerpo enviado, estado HTTP y respuesta.

### 7.4 Casos funcionales de HU-G2-02 · Pagar una deuda

Archivo: `features/g2_pagar_deuda.feature` (20 casos).

| Escenario | CA / regla | Técnica | Casos |
|---|---|---|---|
| Pago exitoso antes del vencimiento (comprobante y saldo) | CA1, CA4 | Camino feliz | 1 |
| Mora de 0.5 % diario con tope de 10 %: días −1, 0, 1, 19, 20, 21 y 60 | CA1 · R-G2-03 | Valores límite | 7 |
| El saldo debe cubrir monto + mora: un céntimo menos / saldo exacto | CA1 · RN-08 | Valores límite | 2 |
| Deuda inexistente → 404 `DEUDA_NO_ENCONTRADA` | CA2 | Partición | 1 |
| Deuda ya pagada → 409 `DEUDA_YA_PAGADA` (el saldo no cambia) | CA2 | Efecto | 1 |
| Deuda en cobranza (61 días) → 422 `DEUDA_EN_COBRANZA` (el saldo no cambia) | CA2 · R-G2-04 | Efecto | 1 |
| Dos pagos simultáneos: uno 201 y otro 409 | CA3 | Concurrencia | 1 |
| El pago genera un movimiento con el mismo código | CA4 · RN-10 | Efecto | 1 |
| Comprobante de otro usuario → 404 | HU-G2-07 CA2 | Seguridad | 1 |
| Pagar sin token → 401 | — | Seguridad | 1 |
| `deuda_id` con tipo inválido: `{}`, `"abc"`, `null` → 422 | — | Técnica (partición) | 3 |

El resto de los casos está en `features/g2_consultar_deudas.feature` (HU-G2-01: empresa, longitud del suministro de 7, 8, 12 y 13 dígitos, formato, orden, campos, estado a los 59, 60 y 61 días, sin deudas) y en `features/g2_debito_automatico.feature` (HU-G2-05).

### 7.5 Validaciones de entrada: dónde se prueba cada una

| Validación | Funcional (`.feature`, diseñadas a mano) | Técnica (Schemathesis, generadas desde el contrato) |
|---|---|---|
| Obligatoriedad (`deuda_id` requerido) | `{}` → 422 | Objetos sin `deuda_id` → 422 |
| Tipo de dato (`deuda_id` entero, cuerpo objeto) | `"abc"`, `null` → 422 | Texto, decimales, booleanos, listas y cuerpos que no son objeto → 422 |
| Rango | Id inexistente (999999) → 404 | Ids cero o negativos → no paga nada |
| Longitud y formato | Suministro de 7, 8, 12 y 13 dígitos; letras, espacios y signo (HU-G2-01) | — (el contrato no define longitudes) |
| Cabecera de autenticación | Sin token → 401 | Sin token y token inválido → 401 |
| Cabecera `Content-Type` | — | Sin `Content-Type` → 422 |
| Métodos HTTP | — | PUT, PATCH, OPTIONS y TRACE en la ruta de pago → 405 |
| Robustez | — | Ningún caso responde 500 |

### 7.6 Resultados y defectos

| Tipo | Casos | Pasan | Fallan |
|---|---|---|---|
| Funcional (incluye la prueba de humo) | 42 | 33 | 9 → 4 defectos |
| Funcional · solo HU-G2-02 | 20 | 16 | 4 → DEF-02 y DEF-03 |
| Técnico · `POST /api/servicios/pagos` | 61 generados | Todos responden bien | 0 errores 500 · 1 observación (cabecera `Allow`) |

| ID | Defecto | Severidad |
|---|---|---|
| DEF-01 | Se acepta un suministro de 13 dígitos (R-G2-01) | Baja |
| DEF-02 | Se cobra mora el mismo día del vencimiento: los días de atraso se cuentan +1 (R-G2-03) | Alta |
| DEF-03 | Una deuda con 60 días pasa a cobranza y no se puede pagar (R-G2-04) | Alta |
| DEF-04 | El débito automático paga deudas ya vencidas y sin mora (HU-G2-05 CA4) | Media |

Las fallas son esperadas: cada una evidencia un defecto real. El detalle, con pasos para reproducir, está en `docs/defectos.md`, y el informe en `docs/informe.md`.

### 7.7 Archivos de las pruebas

| Archivo | Qué es |
|---|---|
| `features/g2_*.feature` | Escenarios Gherkin por HU, con etiquetas `@HU-G2-0x @CAn @técnica` para la trazabilidad |
| `tests/api/conftest.py` | Pasos de pytest-bdd: conectan cada frase del Gherkin con una llamada a la API y su verificación |
| `tests/api/test_g2_pago_servicios.py` | Convierte cada escenario de los `.feature` en una prueba de pytest |
| `tests/tecnico/test_contrato_schemathesis.py` | Prueba técnica: levanta la app, ejecuta Schemathesis y falla si hay un 500 o una validación mal respondida |
| `tests/tecnico/clasificacion_contrato.py` | Clasifica los casos de Schemathesis por validación de entrada y genera su reporte HTML |
| `tests/conftest.py` | Base de datos propia para las pruebas y los resúmenes automáticos de la terminal |
