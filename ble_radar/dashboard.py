from ble_radar.bluehood_layer import enrich_devices_for_session
from html import escape

from ble_radar.device_contract import explain_device, normalize_device
from ble_radar.intel import get_tracker_candidates, get_vendor_summary
from ble_radar.investigation import list_cases
from ble_radar.session_diff import latest_session_diff
from ble_radar.session_catalog import build_session_catalog, latest_session_overview
from ble_radar.artifact_index import build_artifact_index
from ble_radar.state import load_scan_history


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _delta_label(current: int, previous) -> str:
    if previous is None:
        return "n/a"
    diff = current - _safe_int(previous, 0)
    if diff > 0:
        return f"+{diff}"
    return str(diff)


def render_dashboard_html(devices, stamp: str) -> str:
    bluehood_summary = render_bluehood_summary(devices)
    devices = [normalize_device(d) for d in devices]
    history = load_scan_history()[-8:]
    previous = history[-1] if history else None

    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    medium = [d for d in devices if d.get("alert_level") == "moyen"]
    watch_hits = [d for d in devices if d.get("watch_hit")]
    top_hot = sorted(devices, key=lambda d: d.get("final_score", 0), reverse=True)[:10]
    top_trackers = get_tracker_candidates(devices)[:10]
    vendor_counts = get_vendor_summary(devices)[:8]
    cases = list_cases()[:5]
    latest_diff = latest_session_diff()
    recent_sessions = build_session_catalog(limit=5)
    latest_session = latest_session_overview()
    artifact_index = build_artifact_index()

    trend_rows = []
    for row in history:
        trend_rows.append(
            f"<tr><td>{escape(str(row.get('stamp', '-')))}</td>"
            f"<td>{_safe_int(row.get('count', 0))}</td>"
            f"<td>{_safe_int(row.get('critical', 0))}</td>"
            f"<td>{_safe_int(row.get('high', 0))}</td>"
            f"<td>{_safe_int(row.get('medium', 0))}</td></tr>"
        )

    vendor_bars = []
    max_vendor = vendor_counts[0][1] if vendor_counts else 1
    for name, count in vendor_counts:
        pct = int((count / max_vendor) * 100) if max_vendor else 0
        vendor_bars.append(
            f"""
        <div class="bar-row">
            <div class="bar-label">{escape(name)}</div>
            <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div>
            <div class="bar-count">{count}</div>
        </div>
        """
        )

    vendor_options = ['<option value="">Tous les vendors</option>']
    for name, _ in vendor_counts:
        vendor_options.append(f'<option value="{escape(str(name))}">{escape(str(name))}</option>')

    hot_list = []
    for d in top_hot:
        hot_list.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} | {escape(str(d.get('address', '-')))} | "
            f"vendor={escape(str(d.get('vendor', 'Unknown')))} | score={_safe_int(d.get('final_score', 0))} | "
            f"{escape(str(d.get('alert_level', '-')))}</li>"
        )

    tracker_list = []
    for d in top_trackers:
        tracker_list.append(
            f"<li>{escape(str(d.get('name', 'Inconnu')))} | {escape(str(d.get('address', '-')))} | "
            f"follow={_safe_int(d.get('follow_score', 0))} | profile={escape(str(d.get('profile', '-')))}</li>"
        )

    case_list = []
    for case in cases:
        case_list.append(
            f"<li>{escape(str(case.get('title', 'Untitled Case')))} | "
            f"status={escape(str(case.get('status', '-')))} | "
            f"updated={escape(str(case.get('updated_at', '-')))}</li>"
        )

    latest_session_lines = [
        f"<li>Stamp: {escape(str(latest_session.get('stamp', 'unknown')))}</li>",
        f"<li>Devices: {escape(str(latest_session.get('device_count', 0)))}</li>",
        f"<li>Critical: {escape(str(latest_session.get('critical', 0)))}</li>",
        f"<li>Watch hits: {escape(str(latest_session.get('watch_hits', 0)))}</li>",
        f"<li>Trackers: {escape(str(latest_session.get('tracker_candidates', 0)))}</li>",
        f"<li>Top vendor: {escape(str(latest_session.get('top_vendor', 'Unknown')))}</li>",
        f"<li>Top device: {escape(str(latest_session.get('top_device_name', 'Inconnu')))} ({escape(str(latest_session.get('top_device_score', 0)))})</li>",
    ]

    recent_session_lines = []
    for row in recent_sessions:
        recent_session_lines.append(
            f"<li>{escape(str(row.get('stamp', 'unknown')))} | "
            f"devices={escape(str(row.get('device_count', 0)))} | "
            f"critical={escape(str(row.get('critical', 0)))} | "
            f"watch_hits={escape(str(row.get('watch_hits', 0)))} | "
            f"trackers={escape(str(row.get('tracker_candidates', 0)))} | "
            f"top_vendor={escape(str(row.get('top_vendor', 'Unknown')))}</li>"
        )

    artifact_lines = [
        f"<li>Scan manifests: {escape(str(artifact_index.get('scan_manifests', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('scan_manifests', {}).get('latest', 'none') or 'none'))}</li>",
        f"<li>Session diff reports: {escape(str(artifact_index.get('session_diff_reports', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('session_diff_reports', {}).get('latest', 'none') or 'none'))}</li>",
        f"<li>Export contexts: {escape(str(artifact_index.get('export_contexts', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('export_contexts', {}).get('latest', 'none') or 'none'))}</li>",
        f"<li>Incident packs: {escape(str(artifact_index.get('incident_packs', {}).get('count', 0)))} | latest={escape(str(artifact_index.get('incident_packs', {}).get('latest', 'none') or 'none'))}</li>",
    ]

    if latest_diff.get("has_diff"):
        diff_lines = [
            f"<li>Previous: {escape(str(latest_diff.get('previous_stamp', '-')))}</li>",
            f"<li>Current: {escape(str(latest_diff.get('current_stamp', '-')))}</li>",
            f"<li>Devices delta: {escape(str(latest_diff.get('device_count_delta', 0)))}</li>",
            f"<li>Critical delta: {escape(str(latest_diff.get('critical_delta', 0)))}</li>",
            f"<li>Watch hits delta: {escape(str(latest_diff.get('watch_hits_delta', 0)))}</li>",
            f"<li>Trackers delta: {escape(str(latest_diff.get('tracker_candidates_delta', 0)))}</li>",
            f"<li>Top vendor: {escape(str(latest_diff.get('previous_top_vendor', 'Unknown')))} -> {escape(str(latest_diff.get('current_top_vendor', 'Unknown')))}</li>",
            f"<li>Top device: {escape(str(latest_diff.get('previous_top_device', 'Inconnu')))} -> {escape(str(latest_diff.get('current_top_device', 'Inconnu')))}</li>",
        ]
    else:
        diff_lines = ['<li class="muted">Aucun diff comparable disponible</li>']

    comparison_lines = [
        f"<li>Total: {len(devices)} ({_delta_label(len(devices), previous.get('count') if previous else None)} vs précédent)</li>",
        f"<li>Critiques: {len(critical)} ({_delta_label(len(critical), previous.get('critical') if previous else None)} vs précédent)</li>",
        f"<li>Élevés: {len(high)} ({_delta_label(len(high), previous.get('high') if previous else None)} vs précédent)</li>",
        f"<li>Moyens: {len(medium)} ({_delta_label(len(medium), previous.get('medium') if previous else None)} vs précédent)</li>",
    ]

    incident_lines = [
        f"<li>Critiques visibles: {len(critical)}</li>",
        f"<li>Élevés visibles: {len(high)}</li>",
        f"<li>Watchlist Hits: {len(watch_hits)}</li>",
        f"<li>Trackers probables: {len(top_trackers)}</li>",
    ]

    rows = []
    for d in devices:
        css = "normal"
        if d.get("alert_level") == "critique":
            css = "critical"
        elif d.get("alert_level") == "élevé":
            css = "high"
        elif d.get("alert_level") == "moyen":
            css = "medium"

        flags = d.get("flags", [])
        explanation = explain_device(d)["summary"]
        is_tracker = "true" if (d.get("possible_suivi") or d.get("watch_hit") or "tracker" in str(d.get("profile", "")).lower()) else "false"
        is_watch = "true" if d.get("watch_hit") else "false"

        rows.append(
            f"""
        <tr class="{css}" data-alert="{escape(str(d.get('alert_level', 'faible')))}"
            data-vendor="{escape(str(d.get('vendor', 'Unknown')))}"
            data-watch="{is_watch}"
            data-tracker="{is_tracker}">
            <td>{escape(str(d.get("name", "Inconnu")))}</td>
            <td>{escape(str(d.get("address", "-")))}</td>
            <td>{escape(str(d.get("vendor", "Unknown")))}</td>
            <td>{escape(str(d.get("profile", "general_ble")))}</td>
            <td>{escape(str(d.get("rssi", "-")))}</td>
            <td>{escape(str(d.get("risk_score", 0)))}</td>
            <td>{escape(str(d.get("follow_score", 0)))}</td>
            <td>{escape(str(d.get("confidence_score", 0)))}</td>
            <td>{escape(str(d.get("final_score", 0)))}</td>
            <td>{escape(str(d.get("alert_level", "faible")))}</td>
            <td>{escape(str(d.get("seen_count", 0)))}</td>
            <td>{escape(",".join(flags) if flags else "-")}</td>
            <td>{escape(explanation)}</td>
            <td>{escape(str(d.get("reason_short", "normal")))}</td>
        </tr>
        """
        )

    try:
        bluehood_summary = render_bluehood_summary(devices)
    except Exception:
        bluehood_summary = ""

    try:
        bluehood_summary = render_bluehood_summary(devices)
    except Exception:
        bluehood_summary = ""

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BLE Radar Omega AI - Dashboard Pro - {escape(stamp)}</title>
<style>
:root {{
  --bg:#08111e; --panel:#111b2c; --border:#2a3b58; --text:#d7e4f4;
  --blue:#70b7ff; --green:#7df5a3; --yellow:#ffd166; --red:#ff7b7b; --pink:#ff4fa3;
}}
body {{ background:var(--bg); color:var(--text); font-family:ui-monospace,Consolas,monospace; margin:0; padding:24px; }}
h1,h2 {{ color:var(--blue); }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:18px; }}
.card {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; }}
.big {{ font-size:28px; font-weight:700; margin-top:8px; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:18px; }}
.panel {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; }}
input,button,select {{
  background:#0d1523; color:var(--text); border:1px solid var(--border);
  border-radius:10px; padding:10px 12px; margin-right:8px; margin-bottom:8px;
}}
button {{ cursor:pointer; }}
table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--border); border-radius:16px; overflow:hidden; }}
th, td {{ padding:10px 12px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; }}
th {{ color:var(--blue); position:sticky; top:0; background:#0f1a2b; }}
tr.critical {{ background:rgba(255,79,163,.16); }}
tr.high {{ background:rgba(255,123,123,.10); }}
tr.medium {{ background:rgba(255,209,102,.10); }}
tr.normal {{ background:rgba(125,245,163,.06); }}
.table-wrap {{ max-height:65vh; overflow:auto; border-radius:16px; }}
.bar-row {{ display:grid; grid-template-columns:140px 1fr 50px; gap:10px; align-items:center; margin-bottom:8px; }}
.bar-wrap {{ background:#0d1523; border:1px solid var(--border); border-radius:999px; height:14px; overflow:hidden; }}
.bar-fill {{ background:linear-gradient(90deg,var(--blue),var(--green)); height:100%; }}
ul {{ margin:0; padding-left:18px; }}
.muted {{ opacity:.78; }}
.small-table td,.small-table th {{ padding:8px 10px; }}
</style>
</head>
<body>
  <h1>BLE Radar Omega AI - Dashboard Pro</h1>
  <h2>Résumé global</h2>

  <div class="cards">
    <div class="card"><div>Total</div><div class="big">{len(devices)}</div></div>
    <div class="card"><div>Critiques</div><div class="big">{len(critical)}</div></div>
    <div class="card"><div>Élevés</div><div class="big">{len(high)}</div></div>
    <div class="card"><div>Moyens</div><div class="big">{len(medium)}</div></div>
    <div class="card"><div>Watchlist Hits</div><div class="big">{len(watch_hits)}</div></div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Résumé comparatif</h2>
      <ul>{''.join(comparison_lines)}</ul>
      <div class="muted">Horodatage : {escape(stamp)}</div>
    </div>
    <div class="panel">
      <h2>Incidents visibles</h2>
      <ul>{''.join(incident_lines)}</ul>
      <div class="muted">Vue rapide des signaux prioritaires du scan courant.</div>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Cas d'investigation récents</h2>
      <ul>{''.join(case_list) if case_list else '<li class="muted">Aucun cas récent</li>'}</ul>
    </div>
    <div class="panel">
      <h2>Top appareils chauds</h2>
      <ul>{''.join(hot_list) if hot_list else '<li class="muted">Aucun</li>'}</ul>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Top trackers probables</h2>
      <ul>{''.join(tracker_list) if tracker_list else '<li class="muted">Aucun</li>'}</ul>
    </div>
    <div class="panel">
      <h2>Répartition vendors</h2>
      {''.join(vendor_bars) if vendor_bars else '<div class="muted">Aucune donnée</div>'}
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Session diff récent</h2>
    <ul>{''.join(diff_lines)}</ul>
    <div class="muted">Résumé du dernier manifest comparé au précédent.</div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Artifact index</h2>
    <ul>{''.join(artifact_lines)}</ul>
    <div class="muted">Vue rapide des artefacts locaux générés.</div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Latest session overview</h2>
      <ul>{''.join(latest_session_lines)}</ul>
    </div>
    <div class="panel">
      <h2>Sessions récentes</h2>
      <ul>{''.join(recent_session_lines) if recent_session_lines else '<li class="muted">Aucune session récente</li>'}</ul>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Filtres rapides</h2>
      <input id="searchBox" placeholder="Recherche nom / adresse / vendor">
      <select id="vendorSelect">
        {''.join(vendor_options)}
      </select>
      <div>
        <button onclick="setMode('all')">Tout</button>
        <button onclick="setMode('critique')">Critique</button>
        <button onclick="setMode('élevé')">Élevé</button>
        <button onclick="setMode('moyen')">Moyen</button>
        <button onclick="setMode('watch')">Watch hits</button>
        <button onclick="setMode('tracker')">Trackers</button>
      </div>
    </div>
    <div class="panel">
      <h2>Tendance des derniers scans</h2>
      <table class="small-table">
        <thead>
          <tr><th>Scan</th><th>Total</th><th>Critiques</th><th>Élevés</th><th>Moyens</th></tr>
        </thead>
        <tbody>
          {''.join(trend_rows) if trend_rows else '<tr><td colspan="5" class="muted">Aucun historique</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
    <h2>Tableau détaillé des appareils</h2>
    <div class="muted">Vue complète des appareils détectés, scorés et filtrables.</div>
  </div>

  <div class="table-wrap">
    <table id="deviceTable">
      <thead>
        <tr>
          <th>Nom</th>
          <th>Adresse</th>
          <th>Vendor</th>
          <th>Profil</th>
          <th>RSSI</th>
          <th>Risk</th>
          <th>Follow</th>
          <th>Confidence</th>
          <th>Final</th>
          <th>Alerte</th>
          <th>Seen</th>
          <th>Flags</th>
          <th>Explication</th>
          <th>Raison</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>

<script>
const searchBox = document.getElementById('searchBox');
const vendorSelect = document.getElementById('vendorSelect');
let activeMode = 'all';

function rowMatchesMode(tr) {{
  if (activeMode === 'all') return true;
  if (activeMode === 'watch') return tr.dataset.watch === 'true';
  if (activeMode === 'tracker') return tr.dataset.tracker === 'true';
  return tr.dataset.alert === activeMode;
}}

function applyFilters() {{
  const q = searchBox.value.toLowerCase();
  const vendor = vendorSelect.value;

  document.querySelectorAll('#deviceTable tbody tr').forEach(tr => {{
    const txt = tr.innerText.toLowerCase();
    const okText = txt.includes(q);
    const okVendor = !vendor || tr.dataset.vendor === vendor;
    const okMode = rowMatchesMode(tr);
    tr.style.display = okText && okVendor && okMode ? '' : 'none';
  }});
}}

function setMode(mode) {{
  activeMode = mode;
  applyFilters();
}}

searchBox.addEventListener('input', applyFilters);
vendorSelect.addEventListener('change', applyFilters);
</script>

<!-- BLUEHOOD SUMMARY -->
{bluehood_summary}

</body>
</html>
"""


def render_bluehood_summary(devices, registry=None, session_id="dashboard-session", seen_at="now"):
    try:
        enriched = enrich_devices_for_session(
            devices=devices or [],
            registry=registry or {},
            session_id=session_id,
            seen_at=seen_at,
        )
    except Exception as exc:
        return f"""
<section class="panel">
  <h2>Bluehood Summary</h2>
  <ul>
    <li><strong>Status:</strong> error</li>
    <li><strong>Reason:</strong> {escape(str(exc))}</li>
  </ul>
</section>
"""

    correlated_pairs = []
    watch_hits = []

    for item in devices or []:
        if not isinstance(item, dict):
            continue
        address = escape(str(item.get("address", "?")))
        name = escape(str(item.get("name", "Unknown")))

        pair = item.get("correlated_pair") or item.get("correlated_with")
        if pair:
            correlated_pairs.append(f"<li>{address} ↔ {escape(str(pair))} (score: {item.get("score", 0)})</li>")
        else:
            correlated_pairs.append(f"<li>{name} ({address}) — score: {item.get('score', 0)}</li>")

        watch_hits.append(f"<li>{name} ({address})</li>")

    correlated_html = "".join(correlated_pairs) or "<li>None</li>"
    watch_hits_html = "".join(watch_hits) or "<li>None</li>"

    return f"""
<section class="panel">
  <h2>Bluehood Summary</h2>
  <div class="kv"><strong>Total devices:</strong> {len(enriched or [])}</div>
  <h3>Top correlated</h3>
  <ul>
    {correlated_html}
  </ul>
  <h3>Watch hits details</h3>
  <ul>
    {watch_hits_html}
  </ul>
</section>
"""

