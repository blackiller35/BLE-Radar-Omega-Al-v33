def analyze_device(device):
    score = 0
    reasons = []

    name = device.get("name", "Inconnu") or "Inconnu"
    rssi = device.get("rssi", -100)
    address = device.get("address", "")

    if name == "Inconnu":
        score += 30
        reasons.append("nom inconnu")

    if rssi > -50:
        score += 20
        reasons.append("très proche")
    elif rssi > -65:
        score += 10
        reasons.append("proche")

    if len(name) <= 3:
        score += 10
        reasons.append("nom court")

    low = name.lower()

    if "air" in low:
        score += 5
        reasons.append("audio / airtag possible")

    if "tag" in low:
        score += 20
        reasons.append("tag détecté")

    if "watch" in low or "buds" in low or "pods" in low:
        score -= 10
        reasons.append("appareil grand public probable")

    if address.startswith(("DA:", "C2:", "E6:", "F2:")):
        score += 8
        reasons.append("adresse random possible")

    if score >= 40:
        classification = "suspect"
    elif score >= 20:
        classification = "à surveiller"
    else:
        classification = "normal"

    return {
        **device,
        "score": score,
        "classification": classification,
        "reason": ", ".join(reasons) if reasons else "normal",
    }


def analyze_devices(devices):
    return sorted(
        [analyze_device(d) for d in devices],
        key=lambda x: x["score"],
        reverse=True,
    )


def get_top_suspects(devices, min_score=20):
    return [d for d in devices if d.get("score", 0) >= min_score]
