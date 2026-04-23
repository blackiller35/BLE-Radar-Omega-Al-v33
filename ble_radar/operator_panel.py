from __future__ import annotations

import json
from html import escape
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
OPERATOR_PANEL_TEMPLATE = TEMPLATES_DIR / "operator_panel.html"


def _pick(data: dict, *keys: str, default=None):
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return default


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item not in (None, "")]
    if value in ("", None):
        return []
    return [str(value)]


def _risk_score(device: dict) -> int:
    value = _pick(
        device,
        "final_score",
        "threat_score",
        "risk_score",
        "threatScore",
        "score",
        default=0,
    )
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _risk_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _normalize_device(device: dict) -> dict:
    score = _risk_score(device)

    flags = _as_list(_pick(device, "flags", "anomalies", "risk_flags", default=[]))
    if device.get("is_new_device") and "new" not in flags:
        flags.append("new")
    if device.get("persistent_nearby") and "near" not in flags:
        flags.append("near")
    if device.get("possible_suivi") and "tracking" not in flags:
        flags.append("tracking")
    if device.get("watch_hit") and "watch-hit" not in flags:
        flags.append("watch-hit")

    last_seen = _pick(
        device,
        "lastSeen",
        "last_seen",
        "seen_at",
        "timestamp",
        "stamp",
        default="",
    )
    if not last_seen:
        seen_count = device.get("seen_count")
        if seen_count not in (None, ""):
            last_seen = f"seen x{seen_count}"
        else:
            last_seen = "current scan"

    display_score = _pick(
        device,
        "final_score",
        "threat_score",
        "risk_score",
        "threatScore",
        "score",
        default=score,
    )
    try:
        display_score = int(float(display_score))
    except (TypeError, ValueError):
        display_score = score

    return {
        "id": str(_pick(device, "id", "address", "mac", default="unknown-device")),
        "name": str(_pick(device, "name", "display_name", default="Unknown device")),
        "address": str(_pick(device, "address", "mac", default="-")),
        "vendor": str(
            _pick(device, "vendor", "manufacturer", "company", default="Unknown")
        ),
        "rssi": _pick(device, "rssi", default="-"),
        "score": display_score,
        "level": _risk_level(score),
        "last_seen": str(last_seen),
        "summary": str(
            _pick(
                device,
                "ai_summary",
                "summary",
                "reason_short",
                "reason",
                "description",
                default="No summary available.",
            )
        ),
        "services": _as_list(_pick(device, "services", "service_uuids", default=[])),
        "flags": flags,
    }


def _normalize_event(event: dict) -> dict:
    severity = str(_pick(event, "severity", "level", default="low")).lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "low"

    return {
        "severity": severity,
        "title": str(_pick(event, "title", default="Operator event")),
        "message": str(
            _pick(event, "message", "summary", default="No details provided.")
        ),
    }


def _js_json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _paired_dashboard_audit_href(stamp: str) -> str:
    return f"scan_{stamp}.html#security-audit-dedicated-view"


def _render_pills(items: list[str], extra_class: str = "") -> str:
    if not items:
        return '<span class="pill muted">None</span>'
    class_attr = (
        f' class="omega-pills {escape(extra_class)}"'
        if extra_class
        else ' class="omega-pills"'
    )
    pills = "".join(f'<span class="pill">{escape(item)}</span>' for item in items)
    return f"<div{class_attr}>{pills}</div>"


def _render_card(device: dict) -> str:
    level = escape(device["level"])
    name = escape(device["name"])
    address = escape(device["address"])
    vendor = escape(device["vendor"])
    rssi = escape(str(device["rssi"]))
    score = escape(str(device["score"]))
    last_seen = escape(device["last_seen"])
    summary = escape(device["summary"])
    services_count = escape(str(len(device["services"])))
    flags_html = _render_pills(device["flags"], "omega-pills-flags")
    services_html = _render_pills(device["services"])

    return f"""
    <article class="omega-card level-{level}" data-device-id="{escape(device["id"])}">
      <div class="omega-card-inner">
        <section class="omega-face omega-front">
          <div class="omega-top">
            <div>
              <div class="omega-label">Device profile</div>
              <h3>{name}</h3>
              <p class="omega-sub">{address}</p>
            </div>
            <div class="omega-badge">{level.upper()}</div>
          </div>

          <div class="omega-score">
            <span>Display score</span>
            <strong>{score}</strong>
          </div>

          <div class="omega-row"><span>Vendor</span><strong>{vendor}</strong></div>
          <div class="omega-row"><span>RSSI</span><strong>{rssi}</strong></div>
          <div class="omega-row"><span>Last seen</span><strong>{last_seen}</strong></div>
          <div class="omega-row"><span>Services</span><strong>{services_count}</strong></div>

          <div>
            <div class="omega-label">Summary</div>
            <p class="omega-summary">{summary}</p>
          </div>

          <div>
            <div class="omega-label">Flags</div>
            {flags_html}
          </div>

          <div class="omega-actions">
            <button type="button" class="omega-btn js-select">Select</button>
            <button type="button" class="omega-btn omega-btn-primary js-flip">Flip</button>
          </div>
        </section>

        <section class="omega-face omega-back">
          <div class="omega-label">Back side</div>
          <h3>{name}</h3>
          <p class="omega-sub">{vendor} · {level.upper()}</p>

          <div>
            <div class="omega-label">Summary</div>
            <p class="omega-summary">{summary}</p>
          </div>

          <div>
            <div class="omega-label">Services</div>
            {services_html}
          </div>

          <div>
            <div class="omega-label">Flags</div>
            {flags_html}
          </div>

          <div class="omega-actions">
            <button type="button" class="omega-btn js-select">Select</button>
            <button type="button" class="omega-btn omega-btn-primary js-flip">Front</button>
          </div>
        </section>
      </div>
    </article>
    """.strip()


def _render_details(device: dict | None) -> str:
    if not device:
        return '<div class="omega-empty">Aucun appareil sélectionné.</div>'

    services = (
        "".join(f"<li>{escape(service)}</li>" for service in device["services"])
        if device["services"]
        else "<li>No services</li>"
    )
    flags = (
        "".join(f"<li>{escape(flag)}</li>" for flag in device["flags"])
        if device["flags"]
        else "<li>No flags</li>"
    )

    return f"""
    <div class="omega-detail-box">
      <div class="omega-label">Selected device</div>
      <h3>{escape(device["name"])}</h3>
      <p class="omega-sub">{escape(device["address"])} · {escape(device["vendor"])}</p>

      <div class="omega-detail-grid">
        <div><span>Risk</span><strong>{escape(device["level"].upper())}</strong></div>
        <div><span>Score</span><strong>{escape(str(device["score"]))}</strong></div>
        <div><span>RSSI</span><strong>{escape(str(device["rssi"]))}</strong></div>
        <div><span>Services</span><strong>{escape(str(len(device["services"])))}</strong></div>
      </div>

      <div class="omega-label">Summary</div>
      <p class="omega-summary">{escape(device["summary"])}</p>

      <div class="omega-columns">
        <div>
          <div class="omega-label">Services</div>
          <ul>{services}</ul>
        </div>
        <div>
          <div class="omega-label">Flags</div>
          <ul>{flags}</ul>
        </div>
      </div>
    </div>
    """.strip()


def _render_events(events: list[dict]) -> str:
    if not events:
        return '<div class="omega-empty">Aucun événement.</div>'

    chunks = []
    for event in events:
        severity = escape(event["severity"])
        title = escape(event["title"])
        message = escape(event["message"])

        chunks.append(
            f"""
            <article class="omega-event level-{severity}">
              <strong>{title}</strong>
              <p>{message}</p>
            </article>
            """.strip()
        )

    return "\n".join(chunks)


def render_operator_panel_html(
    devices: list[dict], stamp: str, events: list[dict] | None = None
) -> str:
    normalized_devices = [_normalize_device(device) for device in devices]
    normalized_events = [_normalize_event(event) for event in (events or [])]

    cards_html = (
        "\n".join(_render_card(device) for device in normalized_devices)
        if normalized_devices
        else '<div class="omega-empty">Aucun appareil à afficher.</div>'
    )
    details_html = _render_details(
        normalized_devices[0] if normalized_devices else None
    )
    events_html = _render_events(normalized_events)

    html = OPERATOR_PANEL_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "@@CARDS_HTML@@": cards_html,
        "@@DETAILS_HTML@@": details_html,
        "@@EVENTS_HTML@@": events_html,
        "@@STAMP@@": escape(stamp),
        "@@STAMP_JSON@@": _js_json(stamp),
        "@@DEVICES_JSON@@": _js_json(normalized_devices),
        "@@EVENTS_JSON@@": _js_json(normalized_events),
        "@@AUDIT_HREF@@": escape(_paired_dashboard_audit_href(stamp)),
    }
    for needle, value in replacements.items():
        html = html.replace(needle, value)
    return html.strip()
