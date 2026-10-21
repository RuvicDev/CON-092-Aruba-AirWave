# Conector Aruba AirWave (CON-092)

Conector Ruvic de solo lectura para Aruba AirWave Management Platform (API XML): dispositivos, estado, métricas y clientes conectados.

## Instalación

```bash
pip install git+https://github.com/RuvicDev/CON-092-Aruba-AirWave.git#subdirectory=lib
```

Python 3.10+. Dependencias: `requests>=2.31,<3.0`.

## Permisos requeridos

Autenticación por **usuario y contraseña** (formulario `POST /LOGIN`, cookie de sesión).

1. En AirWave, **AMP Setup → Roles → Add** un rol tipo **Monitor Only** (solo lectura) limitado a las carpetas que el agente pueda consultar.
2. **AMP Setup → Users → Add** un usuario dedicado (ej. `ruvic-api`) con ese rol.

## Variables de entorno (`RUVIC_ARUBA_AIRWAVE_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_ARUBA_AIRWAVE_BASE_URL` | Sí | URL de AirWave |
| `RUVIC_ARUBA_AIRWAVE_USERNAME` | Sí | Usuario |
| `RUVIC_ARUBA_AIRWAVE_PASSWORD` | Sí | Contraseña |
| `RUVIC_ARUBA_AIRWAVE_VERIFY_SSL` | No (default `true`) | Verificar certificado SSL |
| `RUVIC_ARUBA_AIRWAVE_CONNECT_TIMEOUT` | No (default `30`) | Timeout de conexión (segundos) |

Los campos opcionales vacíos usan su valor por defecto (la plataforma envía
`""` cuando un campo queda en blanco).

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_ARUBA_AIRWAVE_BASE_URL=...
export RUVIC_ARUBA_AIRWAVE_USERNAME=...
export RUVIC_ARUBA_AIRWAVE_PASSWORD=...

python test_connection.py
python validate_local.py
```

`validate_local.py` lee las métricas, los dispositivos caídos y el detalle del primero.

## Notas de integración

- La API de AirWave es XML; el conector la convierte a dicts (atributos + elementos hijos).
- Si la sesión no es válida AirWave devuelve la página HTML de login (no un 401): el conector lo detecta y reporta error de autenticación.
- Endpoints usados: `ap_list.xml`, `ap_detail.xml?id=`, `amp_stats.xml`, `client_detail.xml?mac=` (verificados contra el cliente de código abierto airwaveapiclient).
- Para certificados autofirmados, desactiva `verify_ssl` solo en redes de confianza.

## Limitaciones conocidas

- Solo lectura: no reinicia equipos ni cambia configuraciones.
- `list_devices` descarga `ap_list.xml` completo y filtra en el conector.
- Los campos de `get_metrics` y `get_client` varían según la versión de AirWave.
