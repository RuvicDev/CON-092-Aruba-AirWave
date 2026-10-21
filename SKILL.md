---
name: aruba-airwave
description: >
  Usa la librería ruvic_aruba_airwave_connector para monitorear (solo
  lectura) la infraestructura Aruba gestionada por AirWave - listar
  dispositivos con su estado y clientes (list_devices), ver el detalle de
  un dispositivo (get_device_status), leer las métricas generales
  (get_metrics) y consultar un cliente conectado por su MAC (get_client).
  Úsala cuando el usuario pregunte por access points caídos, clientes
  WiFi conectados o el estado de la red Aruba en AirWave.
triggers:
- airwave
- aruba airwave
- access point
- ap caido
- clientes wifi
- wifi
- monitoreo de red
---

# Conector Aruba AirWave (ruvic_aruba_airwave_connector)

Librería Python de solo lectura para la API XML de Aruba AirWave. Está **preinstalada en el runtime** cuando el
conector está configurado (si no, instálala con
`pip install git+https://github.com/RuvicDev/CON-092-Aruba-AirWave.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de
variables de entorno, disponibles cuando el conector `aruba_airwave` está
configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_ARUBA_AIRWAVE_BASE_URL` | URL de AirWave |
| `RUVIC_ARUBA_AIRWAVE_USERNAME` | Usuario |
| `RUVIC_ARUBA_AIRWAVE_PASSWORD` | Contraseña |
| `RUVIC_ARUBA_AIRWAVE_VERIFY_SSL` | (opcional) Verificar certificado SSL, default true |
| `RUVIC_ARUBA_AIRWAVE_CONNECT_TIMEOUT` | (opcional) Timeout de conexión (segundos), default 30 |

Si estas variables NO existen, el conector no está configurado: no
generes código que lo use; indica al usuario que lo configure en
**Settings → Conectores**. El código generado **NUNCA** usa nombres con
segmento de alias (`_DEFAULT_INSTANCIA_`, `_PRODUCCION_`, etc.) salvo que
aparezcan en una sección autogenerada `## Variables en tu entorno` al final
de este skill.

## Este conector es de solo lectura

Ninguna operación cambia la configuración de AirWave ni de los equipos.
`list_devices` descarga la lista completa de dispositivos: en redes muy
grandes puede tardar; usa los filtros `status` y `name_contains`.

## Conexión (siempre igual)

```python
from ruvic_aruba_airwave_connector import AirWaveClient

client = AirWaveClient()  # lee RUVIC_ARUBA_AIRWAVE_* del entorno automáticamente
```

## Capacidad 1 — Listar dispositivos

```python
caidos = client.list_devices(status="down")
for d in caidos:
    print(d["id"], d["name"], d["ip"], d["folder"], d["last_contacted"])
```

## Capacidad 2 — Detalle de un dispositivo

```python
d = client.get_device_status(123)
print(d["name"], d["status"], d["uptime"], d["clients"])
for r in d["radios"]:
    print(r["type"], r["channel"], r["clients"])
```

## Capacidad 3 — Métricas generales

```python
m = client.get_metrics()
print(m)
```

Devuelve los contadores tal como los expone `amp_stats.xml` (varían según la versión de AirWave).

## Capacidad 4 — Consultar un cliente conectado

```python
c = client.get_client("12:34:56:78:90:AB")
print(c)
```

## Manejo de errores

```python
from ruvic_aruba_airwave_connector import (
    AirWaveAuthError, AirWaveDataError, AirWaveNetworkError,
)

try:
    client.list_devices(status="down")
except AirWaveAuthError as e:
    print(f"Credenciales o permisos: {e}")
except AirWaveNetworkError as e:
    print(f"No se pudo alcanzar el servicio: {e}")
except AirWaveDataError as e:
    print(f"Error de datos: {e}")
```

Muestra el mensaje de la excepción tal cual al usuario: indica qué corregir.

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_ARUBA_AIRWAVE_*` (el constructor de `AirWaveClient` ya lo hace).
2. Nunca imprimas `RUVIC_ARUBA_AIRWAVE_PASSWORD`.
3. Filtra `list_devices` por estado o nombre: la lista completa puede ser muy grande.
4. Para el detalle de varios equipos, filtra primero con `list_devices` y consulta solo los relevantes.
5. `get_client` necesita la MAC exacta del cliente; si el usuario da un nombre de usuario, explícale que se necesita la MAC.
