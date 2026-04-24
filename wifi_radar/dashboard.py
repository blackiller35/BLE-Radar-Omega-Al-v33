from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from wifi_radar.history import DEFAULT_WIFI_HISTORY_PATH, load_wifi_history, summarize_wifi_history


def _risk_class(level: str) -> str:
    level = str(level or "low").lower()
    if level in {"high", "medium", "low"}:
        return level
    return "low"


def render_wifi_dashboard(history: dict) -> str:
    summary = summarize_wifi_history(history)
    networks = list(history.get("networks", {}).values())
    networks.sort(key=lambda n: (int(n.get("risk_score", 0)), int(n.get("signal", 0))), reverse=True)

    cards = []
    for net in networks:
        risk_level = _risk_class(str(net.get("risk_level", "low")))
        tags = net.get("risk_tags", []) or []
        tag_html = "".join(f'<span class="tag">{escape(str(tag))}</span>' for tag in tags) or '<span class="tag">NONE</span>'

        cards.append(f"""
        <article class="card {risk_level}">
          <div class="card-head">
            <h3>{escape(str(net.get("ssid", "Hidden")))}</h3>
            <span class="risk">{escape(risk_level.upper())} · {escape(str(net.get("risk_score", 0)))}</span>
          </div>
          <p class="bssid">{escape(str(net.get("bssid", "")))}</p>
          <div class="grid">
            <div><strong>Signal</strong><br>{escape(str(net.get("signal", "")))}</div>
            <div><strong>Best</strong><br>{escape(str(net.get("best_signal", "")))}</div>
            <div><strong>Channel</strong><br>{escape(str(net.get("channel", "")))}</div>
            <div><strong>Seen</strong><br>{escape(str(net.get("seen_count", 0)))}</div>
          </div>
          <p><strong>Security:</strong> {escape(str(net.get("security", "UNKNOWN")))}</p>
          <p><strong>First:</strong> {escape(str(net.get("first_seen", "")))}</p>
          <p><strong>Last:</strong> {escape(str(net.get("last_seen", "")))}</p>
          <div class="tags">{tag_html}</div>
        </article>
        """)

    generated = datetime.now().isoformat(timespec="seconds")

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>OMEGA WiFi Dashboard</title>
<style>
body {{
  margin: 0;
  font-family: Arial, sans-serif;
  background: #071018;
  color: #e8f4ff;
}}
header {{
  padding: 28px;
  background: linear-gradient(135deg, #101f2f, #0b3a4a);
  border-bottom: 1px solid #24485a;
}}
h1 {{ margin: 0 0 8px; }}
.summary {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  padding: 20px;
}}
.metric, .card {{
  background: #0d1a25;
  border: 1px solid #24485a;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 0 20px rgba(0,0,0,.25);
}}
.metric strong {{
  display: block;
  font-size: 28px;
}}
.cards {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
  gap: 16px;
  padding: 20px;
}}
.card.high {{ border-color: #ff4d4d; }}
.card.medium {{ border-color: #ffb84d; }}
.card.low {{ border-color: #3ddc97; }}
.card-head {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}}
.card h3 {{ margin: 0; }}
.bssid {{
  color: #9fc7da;
  font-family: monospace;
}}
.risk {{
  padding: 5px 9px;
  border-radius: 999px;
  background: #102b3b;
  white-space: nowrap;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 12px 0;
}}
.grid div {{
  background: #08131c;
  border-radius: 10px;
  padding: 8px;
}}
.tag {{
  display: inline-block;
  margin: 4px 5px 0 0;
  padding: 5px 8px;
  border-radius: 999px;
  background: #16384a;
  color: #d8f5ff;
  font-size: 12px;
}}
footer {{
  padding: 20px;
  color: #9fc7da;
}}
</style>
</head>
<body>
<header>
  <h1>📡 OMEGA WiFi Dashboard</h1>
  <p>Generated at: {escape(generated)}</p>
</header>

<section class="summary">
  <div class="metric"><strong>{summary["total_known_networks"]}</strong>Total known networks</div>
  <div class="metric"><strong>{summary["hidden_networks"]}</strong>Hidden SSID</div>
  <div class="metric"><strong>{summary["medium_or_high_risk"]}</strong>Medium / High risk</div>
  <div class="metric"><strong>{summary["very_close"]}</strong>Very close signal</div>
</section>

<section class="cards">
{''.join(cards)}
</section>

<footer>OMEGA WiFi Radar · Passive local dashboard</footer>
</body>
</html>
"""


def save_wifi_dashboard(
    history_path: str | Path = DEFAULT_WIFI_HISTORY_PATH,
    output_dir: str | Path = "reports/wifi",
) -> Path:
    history = load_wifi_history(history_path)
    html = render_wifi_dashboard(history)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = out / f"wifi_dashboard_{stamp}.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> None:
    path = save_wifi_dashboard()
    print(f"OMEGA WiFi Dashboard saved: {path}")


if __name__ == "__main__":
    main()
