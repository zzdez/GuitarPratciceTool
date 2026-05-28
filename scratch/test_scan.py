import asyncio
import mido
from bleak import BleakScanner

print("--- SCAN MIDI USB (Mido) ---")
try:
    usb_ports = mido.get_input_names()
    print("Ports USB trouvés:", usb_ports)
except Exception as e:
    print("Erreur Mido USB:", e)

print("\n--- SCAN BLE (Bleak) ---")
async def scan_ble():
    try:
        devices = await BleakScanner.discover(timeout=5.0)
        print("Périphériques BLE trouvés:")
        for d in devices:
            print(f"- {d.name} : {d.address} (RSSI: {d.rssi})")
    except Exception as e:
        print("Erreur Bleak BLE:", e)

asyncio.run(scan_ble())
