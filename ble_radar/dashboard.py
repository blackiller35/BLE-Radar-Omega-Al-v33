from html import escape

from ble_radar.state import load_scan_history
from ble_radar.intel import get_vendor_summary, get_tracker_candidates
from ble_radar.device_contract import explain_device


def render_dashboard_html(devices, stamp: str) -> str:
    history = load_scan_history()[-8:]
    critical = [d for d in devices if d.get("alert_level") == "critique"]
    high = [d for d in devices if d.get("alert_level") == "élevé"]
    medium = [d for d in devices if d.get("alert_level") == "moyen"]
    watch_hits = [d for d in devices if d.get("watch_hit")]
    top_hot = sorted(devices, key=lambda d: d.get("final_score", 0), reverse=True)[:10]
    top_trackers = get_tracker_candidates(devices)[:10]
    vendor_counts = get_vendor_summary(devices)[:8]

    trend_rows = []
    for row in history:
        trend_rows.append(
            f"<tr><td>{escape(str(row.get('stamp','-')))}</td><td>{row.get('count',0)}</td><td>{row.get('critical',0)}</td><td>{row.get('high',0)}</td><td>{row.get('medium',0)}</td></tr>"
        )

    vendor_bars = []
    max_vendor = vendor_counts[0][1] if vendor_counts else 1
    for name, count in vendor_counts:
        pct = int((count / max_vendor) * 100) if max_vendor else 0
        vendor_bars.append(f"""
        <div class="bar-row">
            <div class="bar-label">{escape(name)}</div>
            <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div>
            <div class="bar-count">{count}</div>
        </div>
        """)

    hot_list = []
    for d in top_hot:
        hot_list.append(
            f"<li>{escape(str(d.get('name','Inconnu')))} | {escape(str(d.get('address','-')))} | vendor={escape(str(d.get('vendor','Unknown')))} | score={d.get('final_score',0)} | {escape(str(d.get('alert_level','-')))}</li>"
        )

    tracker_list = []
    for d in top_trackers:
        tracker_list.append(
            f"<li>{escape(str(d.get('name','Inconnu')))} | {escape(str(d.get('address','-')))} | follow={d.get('follow_score',0)} | profile={escape(str(d.get('profile','-')))}</li>"
        )

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
        rows.append(f"""
        <tr class="{css}" data-alert="{escape(str(d.get('alert_level','faible')))}" data-vendor="{escape(str(d.get('vendor','Unknown')))}">
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
        """)

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BLE Radar Omega AI - Dashboard - {escape(stamp)}</title>
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
.grid2 {{ display:grid; grid-template-columns:1.1fr .9fr; gap:18px; margin-bottom:18px; }}
.panel {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; }}
input,button {{
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
  <h1>BLE Radar Omega AI - Dashboard</h1>
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
      <h2>Top appareils chauds</h2>
      <ul>{''.join(hot_list) if hot_list else '<li class="muted">Aucun</li>'}</ul>
    </div>
    <div class="panel">
      <h2>Top trackers probables</h2>
      <ul>{''.join(tracker_list) if tracker_list else '<li class="muted">Aucun</li>'}</ul>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2>Répartition vendors</h2>
      {''.join(vendor_bars) if vendor_bars else '<div class="muted">Aucune donnée</div>'}
    </div>
    <div class="panel">
      <h2>Filtres rapides</h2>
      <input id="searchBox" placeholder="Recherche nom / adresse / vendor">
      <div>
        <button onclick="filterRows('all')">Tout</button>
        <button onclick="filterRows('critique')">Critique</button>
        <button onclick="filterRows('élevé')">Élevé</button>
        <button onclick="filterRows('moyen')">Moyen</button>
      </div>
      <div class="muted">Horodatage : {escape(stamp)}</div>
    </div>
  </div>

  <div class="panel" style="margin-bottom:18px;">
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

  <div class="panel" style="margin-bottom:18px;">
    <h2>Tableau détaillé des appareils</h2>
    <div class="muted">Vue complète des appareils détectés et scorés.</div>
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
searchBox.addEventListener('input', () => {{
  const q = searchBox.value.toLowerCase();
  document.querySelectorAll('#deviceTable tbody tr').forEach(tr => {{
    const txt = tr.innerText.toLowerCase();
    tr.style.display = txt.includes(q) ? '' : 'none';
  }});
}});
function filterRows(level) {{
  document.querySelectorAll('#deviceTable tbody tr').forEach(tr => {{
    if (level === 'all') {{
      tr.style.display = '';
    }} else {{
      tr.style.display = tr.dataset.alert === level ? '' : 'none';
    }}
  }});
}}
</script>
</body>
</html>
"""
