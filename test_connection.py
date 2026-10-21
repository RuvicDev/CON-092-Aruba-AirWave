"""Prueba de conexión estándar del conector aruba_airwave.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_ARUBA_AIRWAVE_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Inicia sesión en AirWave y lee las estadísticas generales con las env vars RUVIC_ARUBA_AIRWAVE_*."""
    try:
        from ruvic_aruba_airwave_connector import (
            AirWaveAuthError,
            AirWaveClient,
            AirWaveDataError,
            AirWaveNetworkError,
        )
    except ImportError:
        return (
            False,
            (
                "La librería ruvic-aruba-airwave-connector no está instalada. "
                "Instala con: pip install git+https://github.com/RuvicDev/"
                "CON-092-Aruba-AirWave.git#subdirectory=lib"
            ),
        )

    try:
        client = AirWaveClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except AirWaveAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except AirWaveNetworkError as exc:
        return False, f"Error de red: {exc}"
    except AirWaveDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # noqa: BLE001 - red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a AirWave ({client.config.base_url})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
