"""Validación local del conector aruba_airwave (solo lectura).

Uso:
    python validate_local.py

Requiere RUVIC_ARUBA_AIRWAVE_BASE_URL, RUVIC_ARUBA_AIRWAVE_USERNAME y
RUVIC_ARUBA_AIRWAVE_PASSWORD exportadas.
"""

from ruvic_aruba_airwave_connector import AirWaveClient, setup_logging

setup_logging("INFO")
client = AirWaveClient()

print("== 1. Métricas ==")
print(f"  {client.get_metrics()}")

print("== 2. Dispositivos caídos ==")
caidos = client.list_devices(status="down", limit=10)
for d in caidos:
    print(f"  {d['id']} {d['name']} {d['ip']}")

print("== 3. Detalle del primer dispositivo ==")
todos = client.list_devices(limit=1)
if todos:
    print(f"  {client.get_device_status(todos[0]['id'])}")

print("\nTodo OK.")
