APPLE_PREFIXES = (
    "D8:", "F0:", "A4:", "DC:", "E0:", "3C:", "84:", "94:",
    "B8:", "60:", "28:", "88:", "FC:", "F4:", "AC:", "7C:",
)
SAMSUNG_PREFIXES = ("4C:", "5C:", "7C:", "CC:", "F8:", "30:")
GOOGLE_PREFIXES = ("34:", "F0:", "9F:", "94:", "A8:")
MICROSOFT_PREFIXES = ("BC:", "7E:", "AF:", "00:", "50:")
FITBIT_PREFIXES = ("C8:", "E7:", "5D:")
TILE_HINTS = ("tile", "mate", "slim", "sticker")

def guess_vendor(address: str, name: str = "") -> str:
    addr = (address or "").upper()
    low = (name or "").lower()

    if addr.startswith(APPLE_PREFIXES) or "airtag" in low:
        return "Apple"
    if addr.startswith(SAMSUNG_PREFIXES) or "galaxy" in low:
        return "Samsung"
    if addr.startswith(GOOGLE_PREFIXES) or "pixel" in low:
        return "Google"
    if addr.startswith(MICROSOFT_PREFIXES):
        return "Microsoft"
    if addr.startswith(FITBIT_PREFIXES) or "fitbit" in low:
        return "Fitbit"
    if any(x in low for x in TILE_HINTS):
        return "Tile"
    if "buds" in low or "watch" in low or "phone" in low:
        return "Consumer BLE"
    return "Unknown"
