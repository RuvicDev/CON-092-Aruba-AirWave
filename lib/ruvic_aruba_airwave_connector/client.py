"""Cliente de solo lectura para Aruba AirWave Management Platform (API XML).

Capacidades:
- list_devices():       dispositivos gestionados (APs, controladoras, switches) con estado.
- get_device_status():  detalle de un dispositivo por su ID de AirWave.
- get_metrics():        estadísticas generales de AirWave (amp_stats.xml).
- get_client():         detalle de un cliente conectado por su MAC.

Sesión: POST /LOGIN con usuario y contraseña (cookie de sesión). La API
devuelve XML; el conector lo convierte a dicts.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_ARUBA_AIRWAVE_*
(ver config.AirWaveConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import requests
import urllib3

from .config import AirWaveConfig
from .exceptions import AirWaveAuthError, AirWaveDataError, AirWaveNetworkError
from .logging_utils import get_logger

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


def _to_dict(el: ET.Element) -> Any:
    """Convierte un elemento XML de AirWave en dict (atributos + hijos + texto)."""
    children = list(el)
    if not children and not el.attrib:
        return (el.text or "").strip() or None
    out: dict[str, Any] = dict(el.attrib)
    for child in children:
        value = _to_dict(child)
        if child.tag in out:
            if not isinstance(out[child.tag], list):
                out[child.tag] = [out[child.tag]]
            out[child.tag].append(value)
        else:
            out[child.tag] = value
    text = (el.text or "").strip()
    if text and not children:
        out["value"] = text
    return out


def _text(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value") or value.get("ascii_value")
    return value


def _limit(value: Any, maximum: int = 5000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise AirWaveDataError(f"limit debe ser un entero entre 1 y {maximum}.")
    return value


def _device_summary(d: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": d.get("id"),
        "name": _text(d.get("name")),
        "type": _text(d.get("device_category")) or _text(d.get("mfgr")),
        "model": _text(d.get("model")),
        "ip": _text(d.get("lan_ip")),
        "mac": _text(d.get("lan_mac")),
        "status": "up" if str(_text(d.get("is_up"))).lower() == "true" else "down",
        "clients": int(_text(d.get("client_count")) or 0),
        "folder": _text(d.get("folder")),
        "firmware": _text(d.get("firmware")),
        "last_contacted": _text(d.get("last_contacted")),
    }


class AirWaveClient:
    """Cliente de consulta de Aruba AirWave.

    Args:
        config: configuración. Si se omite, se lee de RUVIC_ARUBA_AIRWAVE_*.

    Ejemplo:
        >>> client = AirWaveClient()
        >>> client.list_devices(status="down")
        [{'id': '123', 'name': 'AP-Piso2-Sala', 'status': 'down', 'clients': 0, ...}]
    """

    def __init__(self, config: AirWaveConfig | None = None) -> None:
        self.config = config or AirWaveConfig.from_env()
        self._logger = get_logger()
        self._session: requests.Session | None = None
        if not self.config.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ------------------------------------------------------------------ #
    # Sesión
    # ------------------------------------------------------------------ #

    def _login(self) -> requests.Session:
        if self._session is not None:
            return self._session
        s = requests.Session()
        s.verify = self.config.verify_ssl
        try:
            resp = s.post(f"{self.config.base_url}/LOGIN", data={
                "credential_0": self.config.username,
                "credential_1": self.config.password,
                "login": "Log In",
                "destination": "/",
                "next_action": "",
            }, timeout=self.config.connect_timeout)
        except requests.exceptions.SSLError as exc:
            raise AirWaveNetworkError(
                "Error de certificado SSL. Si AirWave usa un certificado autofirmado, desactiva "
                "'Verificar certificado SSL' en la configuración del conector."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise AirWaveNetworkError(f"No se pudo alcanzar AirWave ({self.config.base_url}): {exc}") from exc
        if resp.status_code >= 500:
            raise AirWaveNetworkError(f"AirWave respondió {resp.status_code} al iniciar sesión.")
        self._session = s
        return s

    def _get_xml(self, path: str, params: Any = None) -> ET.Element:
        s = self._login()
        try:
            resp = s.get(f"{self.config.base_url}/{path}", params=params, timeout=self.config.connect_timeout)
        except requests.exceptions.RequestException as exc:
            raise AirWaveNetworkError(f"Error de red consultando {path}: {exc}") from exc
        body = resp.text or ""
        # Si la sesión no es válida AirWave devuelve la página HTML de login, no un 401
        if resp.status_code in (401, 403) or "credential_0" in body or body.lstrip().lower().startswith("<!doctype html"):
            self._session = None
            raise AirWaveAuthError("Usuario o contraseña de AirWave inválidos, o el rol no permite usar la API.")
        if resp.status_code == 404:
            raise AirWaveDataError(f"AirWave no tiene el recurso {path}.")
        if resp.status_code >= 400:
            raise AirWaveDataError(f"AirWave respondió {resp.status_code}: {body[:200]}")
        try:
            return ET.fromstring(resp.content)
        except ET.ParseError as exc:
            raise AirWaveDataError(f"AirWave devolvió un XML inválido en {path}.") from exc

    def ping(self) -> bool:
        """Verifica credenciales leyendo las estadísticas generales.

        Raises:
            AirWaveAuthError / AirWaveNetworkError / AirWaveDataError.
        """
        self._get_xml("amp_stats.xml")
        self._logger.info("Ping exitoso a AirWave %s", self.config.base_url)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: dispositivos
    # ------------------------------------------------------------------ #

    def list_devices(self, status: str | None = None, name_contains: str | None = None,
                     limit: int = 200) -> list[dict[str, Any]]:
        """Lista los dispositivos gestionados con su estado y clientes conectados.

        Args:
            status: "up" o "down" para filtrar (opcional).
            name_contains: texto en el nombre (opcional).
            limit: máximo de dispositivos (1-5000).

        Returns:
            Lista de dicts: id, name, type, model, ip, mac, status, clients,
            folder, firmware, last_contacted.

        Ejemplo:
            >>> client.list_devices(status="down")
            [{'id': '123', 'name': 'AP-Piso2', 'status': 'down', ...}]
        """
        limit = _limit(limit)
        if status is not None and status not in ("up", "down"):
            raise AirWaveDataError("status debe ser 'up' o 'down'.")
        root = self._get_xml("ap_list.xml")
        needle = (name_contains or "").lower()
        out = []
        for el in root.iter("ap"):
            d = _device_summary(_to_dict(el))
            if status and d["status"] != status:
                continue
            if needle and needle not in str(d["name"] or "").lower():
                continue
            out.append(d)
            if len(out) >= limit:
                break
        self._logger.info("Dispositivos listados: %d", len(out))
        return out

    # ------------------------------------------------------------------ #
    # Capacidad 2: estado de un dispositivo
    # ------------------------------------------------------------------ #

    def get_device_status(self, device_id: str | int) -> dict[str, Any]:
        """Consulta el detalle de un dispositivo (radios, uptime, clientes).

        Args:
            device_id: ID numérico de AirWave (campo 'id' de list_devices).

        Returns:
            Dict con el resumen del dispositivo más 'radios' (lista con
            índice, canal, potencia y clientes por radio) y 'uptime'.

        Ejemplo:
            >>> client.get_device_status(123)
            {'id': '123', 'name': 'AP-Piso2', 'status': 'up', 'radios': [...], ...}
        """
        if not str(device_id).isdigit():
            raise AirWaveDataError(f"device_id debe ser el ID numérico de AirWave, no {device_id!r}.")
        root = self._get_xml("ap_detail.xml", params={"id": str(device_id)})
        el = next(root.iter("ap"), None)
        if el is None:
            raise AirWaveDataError(f"No existe el dispositivo con ID {device_id} en AirWave.")
        raw = _to_dict(el)
        result = _device_summary(raw)
        radios = raw.get("radio") or []
        if isinstance(radios, dict):
            radios = [radios]
        result["uptime"] = _text(raw.get("uptime")) or _text(raw.get("snmp_uptime"))
        result["radios"] = [{
            "index": r.get("index"),
            "type": _text(r.get("radio_type")),
            "channel": _text(r.get("channel")),
            "transmit_power": _text(r.get("transmit_power")),
            "clients": _text(r.get("client_count")),
        } for r in radios if isinstance(r, dict)]
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 3: métricas generales
    # ------------------------------------------------------------------ #

    def get_metrics(self) -> dict[str, Any]:
        """Lee las estadísticas generales de AirWave (dispositivos arriba/abajo,
        clientes, alertas, etc.).

        Returns:
            Dict con los contadores tal como los expone amp_stats.xml.

        Ejemplo:
            >>> client.get_metrics()
            {'devices_up': '210', 'devices_down': '3', 'clients': '1543', ...}
        """
        root = self._get_xml("amp_stats.xml")
        data = _to_dict(root)
        return data if isinstance(data, dict) else {"value": data}

    # ------------------------------------------------------------------ #
    # Capacidad 4: cliente conectado
    # ------------------------------------------------------------------ #

    def get_client(self, mac: str) -> dict[str, Any]:
        """Consulta un cliente (dispositivo de usuario) por su MAC.

        Args:
            mac: MAC del cliente, ej. "12:34:56:78:90:AB".

        Returns:
            Dict con el detalle de la asociación (AP, SSID, usuario, IP,
            señal, etc.) tal como lo devuelve client_detail.xml.

        Ejemplo:
            >>> client.get_client("12:34:56:78:90:AB")
            {'mac': '12:34:56:78:90:AB', 'ap': 'AP-Piso2', 'ssid': 'Corporativa', ...}
        """
        if not isinstance(mac, str) or not _MAC_RE.match(mac.strip()):
            raise AirWaveDataError(f"mac inválida: {mac!r}. Formato esperado 12:34:56:78:90:AB.")
        mac = mac.strip().upper().replace("-", ":")
        root = self._get_xml("client_detail.xml", params={"mac": mac})
        el = next(root.iter("client"), None)
        if el is None:
            raise AirWaveDataError(f"AirWave no tiene registro del cliente {mac}.")
        data = _to_dict(el)
        if isinstance(data, dict):
            data.setdefault("mac", mac)
        return data
