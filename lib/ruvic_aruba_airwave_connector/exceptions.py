"""Excepciones propias del conector Aruba AirWave.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del cliente HTTP subyacente.
"""


class AirWaveConnectorError(Exception):
    """Error base del conector."""


class AirWaveAuthError(AirWaveConnectorError):
    """Credenciales inválidas o permisos insuficientes."""


class AirWaveNetworkError(AirWaveConnectorError):
    """No se pudo alcanzar el servicio (red, timeout o error del servidor)."""


class AirWaveDataError(AirWaveConnectorError):
    """La operación es válida pero los datos o parámetros no lo son."""
