"""Monitoreo de infraestructura Aruba con AirWave (API XML): consultar dispositivos y su estado, métricas generales y clientes conectados. Solo lectura"""

from .client import AirWaveClient
from .config import ENV_PREFIX, AirWaveConfig
from .exceptions import (
    AirWaveAuthError,
    AirWaveConnectorError,
    AirWaveDataError,
    AirWaveNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "AirWaveAuthError",
    "AirWaveClient",
    "AirWaveConfig",
    "AirWaveConnectorError",
    "AirWaveDataError",
    "AirWaveNetworkError",
    "ENV_PREFIX",
    "setup_logging",
]

__version__ = "1.0.0"
