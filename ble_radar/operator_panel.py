from __future__ import annotations

from html import escape
import json


def _pick(data: dict, *keys: str, default=""):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v not in (None, "")]
    if value == "":
        return []
    return [str(value)]


def _risk_score(device: dict) -> int:
    raw = _pick(device, "risk_score", "threatScore", "score", default=0)
    try:
        return int(float(raw))
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
    return {
        "id": str(_pick(device, "id", "address", "mac", default="unknown-device")),
        "name": str(_pick(device, "name", "display_name", default="Unknown device")),
        "address": str(_pick(device, "address", "mac", default="-")),
        "vendor": str(_pick(device, "vendor", "manufacturer", default="Unknown")),
        "rssi": _pick(device, "rssi", default="-"),
        "score": score,
        "level": _risk_level(score),
        "summary": str(
            _pick(
                device,
                "ai_summary",
                "summary",
                "description",
                default="No summary available.",
            )
        ),
        "services": _as_list(_pick(device, "services", "service_uuids", default=[])),
        "flags": _as_list(_pick(device, "flags", "anomalies", "risk_flags", default=[])),
    }


def _normalize_event(event: dict) -> dict:
    severity = str(_pick(event, "severity", default="medium")).lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"
    return {
        "title": str(_pick(event, "title", default="Event")),
        "message": str(_pick(event, "message", default="")),
        "severity": severity,
    }


def _js_json(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _render_card(device: dict) -> str:
    services = "".join(
        f'<span class="pill">{escape(service)}</span>'
        for service in device["services"][:3]
    ) or '<span class="pill muted">No services</span>'

    flags = "".join(
        f'<span class="pill pill-alert">{escape(flag)}</span>'
        for flag in device["flags"][:3]
    ) or '<span class="pill muted">No flags</span>'

    return f"""
<article class="omega-card level-{escape(device['level'])}" data-device-id="{escape(device['id'])}">
  <div class="omega-card-inner">
    <section class="omega-face omega-front">
      <div class="omega-top">
        <div>
          <div class="omega-label">Device profile</div>
          <h3>{escape(device['name'])}</h3>
          <p class="omega-sub">{escape(device['address'])}</p>
        </div>
        <span class="omega-badge">{escape(device['level']).upper()}</span>
      </div>

      <div class="omega-score">
        <strong>{escape(str(device['score']))}</strong>
        <span>risk score</span>
      </div>

      <div class="omega-row">
        <span>Vendor</span>
        <strong>{escape(device['vendor'])}</strong>
      </div>

      <div class="omega-row">
        <span>RSSI</span>
        <strong>{escape(str(device['rssi']))}</strong>
      </div>

      <p class="omega-summary">{escape(device['summary'])}</p>

      <div class="omega-group">
        <div class="omega-label">Services</div>
        <div class="omega-pills">{services}</div>
      </div>

      <div class="omega-actions">
        <button type="button" class="omega-btn js-select">Select</button>
        <button type="button" class="omega-btn omega-btn-primary js-flip">Details</button>
      </div>
    </section>

    <section class="omega-face omega-back">
      <div class="omega-top">
        <div>
          <div class="omega-label">Back side</div>
          <h3>{escape(device['name'])}</h3>
          <p class="omega-sub">{escape(device['vendor'])}</p>
        </div>
        <span class="omega-badge">{escape(device['level']).upper()}</span>
      </div>

      <div class="omega-group">
        <div class="omega-label">Flags</div>
        <div class="omega-pills">{flags}</div>
      </div>

      <div class="omega-group">
        <div class="omega-label">Summary</div>
        <p class="omega-summary">{escape(device['summary'])}</p>
      </div>

      <div class="omega-actions">
        <button type="button" class="omega-btn js-select">Show right panel</button>
        <button type="button" class="omega-btn omega-btn-primary js-flip">Return</button>
      </div>
    </section>
  </div>
</article>
""".strip()


def _render_details(device: dict | None) -> str:
    if not device:
        return '<div class="omega-empty">Aucun appareil sélectionné.</div>'

    services = "".join(
        f"<li>{escape(service)}</li>" for service in device["services"]
    ) or "<li>No services</li>"

    flags = "".join(
        f"<li>{escape(flag)}</li>" for flag in device["flags"]
    ) or "<li>No flags</li>"

    return f"""
<div class="omega-detail-box">
  <div class="omega-label">Selected device</div>
  <h3>{escape(device['name'])}</h3>
  <p class="omega-sub">{escape(device['address'])} · {escape(device['vendor'])}</p>

  <div class="omega-detail-grid">
    <div><span>Risk</span><strong>{escape(device['level']).upper()}</strong></div>
    <div><span>Score</span><strong>{escape(str(device['score']))}</strong></div>
    <div><span>RSSI</span><strong>{escape(str(device['rssi']))}</strong></div>
    <div><span>Services</span><strong>{escape(str(len(device['services'])))}</strong></div>
  </div>

  <div class="omega-label">Summary</div>
  <p class="omega-summary">{escape(device['summary'])}</p>

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

    parts = []
    for event in events:
        parts.append(
            f"""
<div class="omega-event level-{escape(event['severity'])}">
  <strong>{escape(event['title'])}</strong>
  <p>{escape(event['message'])}</p>
</div>
""".strip()
        )
    return "\n".join(parts)


def _paired_dashboard_audit_href(stamp: str) -> str:
    safe_stamp = str(stamp).strip()
    return f"scan_{safe_stamp}.html#security-audit-dedicated-view"


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
    details_html = _render_details(normalized_devices[0] if normalized_devices else None)
    events_html = _render_events(normalized_events)

    devices_json = _js_json(normalized_devices)
    events_json = _js_json(normalized_events)
    stamp_json = _js_json(stamp)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BLE Radar Omega AI — Operator Panel</title>
<style>
:root {{
  --bg:#071018;
  --panel:#0d1824;
  --panel-2:#0f1d2b;
  --line:rgba(120,194,255,.18);
  --text:#d9efff;
  --muted:#86a3b9;
  --accent:#59d7ff;
  --low:#39ffb6;
  --medium:#ffb84d;
  --high:#ff6d6d;
  --critical:#ff3f88;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:Inter,system-ui,sans-serif;
  color:var(--text);
  background:linear-gradient(180deg,#03070c 0%,#071018 55%,#08131d 100%);
}}
.app {{
  width:min(1500px, calc(100% - 28px));
  margin:20px auto 32px;
}}
.panel {{
  background:linear-gradient(180deg, rgba(13,24,36,.94), rgba(9,17,26,.94));
  border:1px solid var(--line);
  border-radius:22px;
  box-shadow:0 18px 44px rgba(0,0,0,.35);
}}
.topbar {{
  padding:20px;
  margin-bottom:18px;
}}
.topbar h1 {{
  margin:0 0 8px;
  font-size:2rem;
}}
.topbar p {{
  margin:0;
  color:var(--muted);
}}
.top-stamp {{
  margin-top:12px;
  font-size:.9rem;
  color:var(--accent);
}}
.layout {{
  display:grid;
  grid-template-columns:1.65fr 1fr;
  gap:18px;
}}
.cards,
.sidebar {{
  padding:18px;
}}
.cards-head,
.side-head {{
  margin-bottom:14px;
}}
.cards-head h2,
.side-head h2 {{
  margin:0 0 6px;
  font-size:1.08rem;
}}
.cards-head p,
.side-head p {{
  margin:0;
  color:var(--muted);
}}
.cards-grid {{
  display:grid;
  grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));
  gap:16px;
}}
.omega-card {{
  min-height:360px;
  perspective:1200px;
}}
.omega-card-inner {{
  position:relative;
  min-height:360px;
  transform-style:preserve-3d;
  transition:transform .6s ease;
}}
.omega-card.is-flipped .omega-card-inner {{
  transform:rotateY(180deg);
}}
.omega-face {{
  position:absolute;
  inset:0;
  display:flex;
  flex-direction:column;
  gap:12px;
  padding:18px;
  border-radius:18px;
  border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(15,29,43,.96), rgba(8,18,28,.96));
  backface-visibility:hidden;
}}
.omega-back {{
  transform:rotateY(180deg);
}}
.omega-top {{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:12px;
}}
.omega-top h3 {{
  margin:4px 0 0;
  font-size:1.1rem;
}}
.omega-label {{
  font-size:.74rem;
  text-transform:uppercase;
  letter-spacing:.14em;
  color:var(--accent);
}}
.omega-sub {{
  margin:6px 0 0;
  color:var(--muted);
  font-size:.9rem;
}}
.omega-badge {{
  padding:8px 10px;
  border-radius:999px;
  font-size:.74rem;
  font-weight:800;
  border:1px solid currentColor;
}}
.omega-score {{
  padding:14px;
  border-radius:16px;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.06);
}}
.omega-score strong {{
  display:block;
  font-size:2rem;
  line-height:1;
}}
.omega-score span,
.omega-row span,
.omega-detail-grid span {{
  color:var(--muted);
}}
.omega-row {{
  display:flex;
  justify-content:space-between;
  gap:12px;
  padding:12px 14px;
  border-radius:14px;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.06);
}}
.omega-summary {{
  margin:0;
  color:#d9e7f4;
  line-height:1.5;
  font-size:.93rem;
}}
.omega-pills {{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
}}
.pill {{
  padding:8px 10px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.08);
  background:rgba(255,255,255,.04);
  font-size:.8rem;
}}
.pill-alert {{
  background:rgba(255,109,109,.08);
  border-color:rgba(255,109,109,.22);
}}
.muted {{
  color:var(--muted);
}}
.omega-actions {{
  display:flex;
  gap:10px;
  margin-top:auto;
}}
.omega-btn {{
  flex:1;
  padding:11px 12px;
  border-radius:14px;
  border:1px solid var(--line);
  background:rgba(8,19,28,.84);
  color:var(--text);
  cursor:pointer;
}}
.omega-btn-primary {{
  background:linear-gradient(135deg, rgba(89,215,255,.20), rgba(111,124,255,.16));
}}
.omega-detail-box {{
  padding:16px;
  border-radius:18px;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.06);
}}
.omega-detail-box h3 {{
  margin:4px 0 0;
}}
.omega-detail-grid {{
  display:grid;
  grid-template-columns:repeat(2, 1fr);
  gap:10px;
  margin:14px 0;
}}
.omega-detail-grid > div {{
  padding:12px;
  border-radius:14px;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.06);
}}
.omega-detail-grid strong {{
  display:block;
  margin-top:6px;
}}
.omega-columns {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:14px;
}}
.omega-columns ul {{
  margin:8px 0 0;
  padding-left:18px;
  color:#d9e7f4;
}}
.omega-events {{
  margin-top:18px;
}}
.omega-event {{
  padding:12px 14px;
  border-radius:14px;
  margin-bottom:10px;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.06);
}}
.omega-event strong {{
  display:block;
  margin-bottom:4px;
}}
.omega-event p {{
  margin:0;
  color:var(--muted);
}}
.omega-empty {{
  padding:24px;
  border-radius:18px;
  border:1px dashed rgba(255,255,255,.12);
  color:var(--muted);
  text-align:center;
}}
.level-low .omega-badge,
.omega-event.level-low {{ color:var(--low); }}
.level-medium .omega-badge,
.omega-event.level-medium {{ color:var(--medium); }}
.level-high .omega-badge,
.omega-event.level-high {{ color:var(--high); }}
.level-critical .omega-badge,
.omega-event.level-critical {{ color:var(--critical); }}
@media (max-width: 1100px) {{
  .layout {{ grid-template-columns:1fr; }}
}}
@media (max-width: 720px) {{
  .omega-detail-grid,
  .omega-columns {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
  <main class="app">
    <section class="panel topbar">
      <div class="omega-label">OMEGA / Operator Panel Foundation</div>
      <h1>BLE Radar Omega AI</h1>
      <p>Separate operator panel foundation with device profile cards, front/back flip, selected details, and event journal.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">
        <a
          class="omega-btn"
          href="{escape(_paired_dashboard_audit_href(stamp))}"
          onclick="try{{window.localStorage.setItem('bleRadarSecurityAuditFilter','all')}}catch(_err){{}}"
          style="text-decoration:none;display:inline-flex;align-items:center;justify-content:center;"
        >Open security audit view</a>
      </div>
      <div class="top-stamp">Generated at: {escape(stamp)}</div>
    </section>

    <section class="layout">
      <section class="panel cards">
        <div class="cards-head">
          <h2>Device Profiles</h2>
          <p>Safe standalone foundation for later live BLE data integration.</p>
        </div>
        <div class="cards-grid">
          {cards_html}
        </div>
      </section>

      <aside>
        <section class="panel sidebar">
          <div class="side-head">
            <h2>Selected Device</h2>
            <p>Right-side context panel.</p>
          </div>
          <div id="omega-details">{details_html}</div>
        </section>

        <section class="panel sidebar omega-events">
          <div class="side-head">
            <h2>Event Journal</h2>
            <p>Simple operator event stream.</p>
          </div>
          <div id="omega-events">{events_html}</div>
        </section>
      </aside>
    </section>
  </main>

<script>
window.BleRadarOmegaUI = {{
  devices: {devices_json},
  events: {events_json},
  stamp: {stamp_json}
}};

(function () {{
  const detailsEl = document.getElementById("omega-details");
  const cards = document.querySelectorAll(".omega-card");

  function escapeHtml(value) {{
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }}

  function renderDetails(device) {{
    if (!device) {{
      detailsEl.innerHTML = '<div class="omega-empty">Aucun appareil sélectionné.</div>';
      return;
    }}

    const services = (device.services || []).length
      ? device.services.map(service => `<li>${{escapeHtml(service)}}</li>`).join("")
      : "<li>No services</li>";

    const flags = (device.flags || []).length
      ? device.flags.map(flag => `<li>${{escapeHtml(flag)}}</li>`).join("")
      : "<li>No flags</li>";

    detailsEl.innerHTML = `
      <div class="omega-detail-box">
        <div class="omega-label">Selected device</div>
        <h3>${{escapeHtml(device.name)}}</h3>
        <p class="omega-sub">${{escapeHtml(device.address)}} · ${{escapeHtml(device.vendor)}}</p>

        <div class="omega-detail-grid">
          <div><span>Risk</span><strong>${{escapeHtml(device.level.toUpperCase())}}</strong></div>
          <div><span>Score</span><strong>${{escapeHtml(String(device.score))}}</strong></div>
          <div><span>RSSI</span><strong>${{escapeHtml(String(device.rssi))}}</strong></div>
          <div><span>Services</span><strong>${{escapeHtml(String((device.services || []).length))}}</strong></div>
        </div>

        <div class="omega-label">Summary</div>
        <p class="omega-summary">${{escapeHtml(device.summary)}}</p>

        <div class="omega-columns">
          <div>
            <div class="omega-label">Services</div>
            <ul>${{services}}</ul>
          </div>
          <div>
            <div class="omega-label">Flags</div>
            <ul>${{flags}}</ul>
          </div>
        </div>
      </div>
    `;
  }}

  function selectDevice(id) {{
    const device = (window.BleRadarOmegaUI.devices || []).find(item => item.id === id);
    renderDetails(device || null);
  }}

  cards.forEach(card => {{
    const deviceId = card.dataset.deviceId;

    card.querySelectorAll(".js-flip").forEach(button => {{
      button.addEventListener("click", function (event) {{
        event.preventDefault();
        event.stopPropagation();
        card.classList.toggle("is-flipped");
      }});
    }});

    card.querySelectorAll(".js-select").forEach(button => {{
      button.addEventListener("click", function (event) {{
        event.preventDefault();
        event.stopPropagation();
        selectDevice(deviceId);
      }});
    }});

    card.addEventListener("click", function (event) {{
      if (event.target.closest("button")) {{
        return;
      }}
      selectDevice(deviceId);
    }});
  }});
}})();
</script>
</body>
</html>
""".strip()
