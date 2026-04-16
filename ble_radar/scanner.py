from bleak import BleakScanner
import asyncio

async def scan_ble(timeout=5):
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    results = []

    for d, adv in devices.values():
        results.append({
            "name": d.name or "Inconnu",
            "address": d.address,
            "rssi": adv.rssi,
        })

    return results

def run_scan(timeout=5):
    return asyncio.run(scan_ble(timeout))
