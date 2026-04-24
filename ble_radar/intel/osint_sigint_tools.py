def get_intel_tools(tags: list[str]) -> list[str]:
    tools = []

    if "TRACKING_SUSPECT" in tags:
        tools += ["nRF Sniffer", "Wireshark BLE"]

    if "PERSISTENT_DEVICE" in tags:
        tools += ["Kismet", "tshark"]

    if "HIGH_ACTIVITY" in tags:
        tools += ["Wireshark", "BLE Analyzer"]

    if "RANDOMIZED_BLE_ADDRESS" in tags:
        tools += ["nRF Sniffer"]

    if not tools:
        tools.append("No specific tools")

    return sorted(set(tools))
