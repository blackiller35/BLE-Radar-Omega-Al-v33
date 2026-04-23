from ble_radar.operator_panel import render_operator_panel_html


def test_operator_panel_contains_device_profiles_and_bridge():
    html = render_operator_panel_html(
        [
            {
                "address": "AA:BB:CC:DD:EE:FF",
                "name": "Beacon A17",
                "vendor": "Nordic",
                "rssi": -48,
                "risk_score": 91,
                "services": ["iBeacon", "Telemetry"],
                "flags": ["Spoofing suspect"],
                "summary": "High confidence anomaly.",
            }
        ],
        "2026-04-22 16:55",
        events=[
            {
                "severity": "critical",
                "title": "Spoofing BLE suspect",
                "message": "Identity rotation anomaly.",
            }
        ],
    )

    assert "BLE Radar Omega AI" in html
    assert "Beacon A17" in html
    assert "AA:BB:CC:DD:EE:FF" in html
    assert "Device Profiles" in html
    assert "Selected Device" in html
    assert "Event Journal" in html
    assert "window.BleRadarOmegaUI" in html
    assert "CRITICAL" in html


def test_operator_panel_empty_state():
    html = render_operator_panel_html([], "2026-04-22 16:55", events=[])

    assert "Aucun appareil à afficher." in html
    assert "Aucun événement." in html


def test_operator_panel_contains_security_audit_jump():
    html = render_operator_panel_html([], "2026-04-22_16-55-00", events=[])

    assert "Open security audit view" in html
    assert 'href="scan_2026-04-22_16-55-00.html#security-audit-dedicated-view"' in html
    assert "bleRadarSecurityAuditFilter" in html


def test_operator_panel_contains_selected_card_ui():
    html = render_operator_panel_html(
        [
            {
                "address": "AA:BB:CC:DD:EE:FF",
                "name": "Beacon A17",
                "vendor": "Nordic",
                "rssi": -48,
                "risk_score": 91,
                "services": ["iBeacon", "Telemetry"],
                "flags": ["Spoofing suspect"],
                "summary": "High confidence anomaly.",
            }
        ],
        "2026-04-22 16:55",
        events=[],
    )

    assert '.omega-card.is-selected .omega-face' in html
    assert 'card.classList.toggle("is-selected", card.dataset.deviceId === id);' in html
