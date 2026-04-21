import unicodedata


def normalize_command(text: str) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def parse_command(text: str) -> dict:
    raw = normalize_command(text)
    parts = raw.split()

    if not parts:
        return {"action": "none"}

    first = parts[0]
    rest = " ".join(parts[1:]).strip()

    if first in ("scan", "scanner"):
        return {"action": "scan"}
    if first in ("alerts", "alertes"):
        return {"action": "alerts"}
    if first in ("trackers", "tracker"):
        return {"action": "trackers"}
    if first in ("invest", "investigation"):
        return {"action": "investigation"}
    if first in ("views", "vues"):
        return {"action": "views"}
    if first in ("history", "historique"):
        return {"action": "history"}
    if first in ("compare", "comparaison"):
        return {"action": "compare"}
    if first in ("suggest", "suggestions"):
        return {"action": "suggestions"}
    if first in ("audit", "export"):
        return {"action": "audit"}
    if first in ("html", "report"):
        return {"action": "open_html"}
    if first in ("metrics", "metriques", "métriques", "anomalies"):
        return {"action": "metrics"}
    if first in ("replay", "lab"):
        return {"action": "replay"}
    if first in ("profiles", "profile", "profil"):
        return {"action": "profile", "query": rest}

    if first == "session" and len(parts) > 1:
        if parts[1] == "unlock":
            return {"action": "operator_session_unlock"}
        if parts[1] == "lock":
            return {"action": "operator_session_lock"}
        if parts[1] == "status":
            return {"action": "operator_session_status"}
        if parts[1] == "clear":
            return {"action": "operator_session_clear"}

    if first in ("session_unlock", "opunlock"):
        return {"action": "operator_session_unlock"}
    if first in ("session_lock", "oplock"):
        return {"action": "operator_session_lock"}
    if first in ("session_status", "opstatus"):
        return {"action": "operator_session_status"}
    if first in ("session_clear", "opclear"):
        return {"action": "operator_session_clear"}

    if first in ("search", "find", "query", "recherche") and rest:
        return {"action": "search_last", "query": rest}
    if first in ("hist", "searchhist", "recherchehist") and rest:
        return {"action": "search_history", "query": rest}

    if first in ("critical", "critique"):
        return {"action": "view_critical"}
    if first in ("high", "eleve", "élevé"):
        return {"action": "view_high"}
    if first in ("watchhits", "watchhit"):
        return {"action": "view_watch_hits"}
    if first in ("new", "nouveau"):
        return {"action": "view_new"}
    if first in ("near", "proche"):
        return {"action": "view_near"}
    if first == "apple":
        return {"action": "view_apple"}
    if first == "random":
        return {"action": "view_random"}
    if first in ("unknown", "inconnu"):
        return {"action": "view_unknown_vendor"}

    return {"action": "unknown", "raw": raw}


def command_help_lines():
    return [
        "scan",
        "alerts",
        "trackers",
        "investigation",
        "views",
        "history",
        "compare",
        "suggestions",
        "audit",
        "metrics",
        "replay",
        "profile balanced",
        "profile paranoid",
        "profile tracker_hunt",
        "profile quiet",
        "session unlock",
        "session lock",
        "session status",
        "html",
        "search apple",
        "search tracker",
        "hist apple",
        "critical",
        "high",
        "watchhits",
        "new",
        "near",
        "random",
        "unknown",
    ]
