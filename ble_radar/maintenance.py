from pathlib import Path

DEFAULT_RUNTIME_ARTIFACT_PATTERNS = (
    "reports/scan_*.json",
    "reports/scan_*.csv",
    "reports/scan_*.txt",
    "reports/scan_*.html",
    "reports/release_summary_*.md",
    "history/executive_summary_*.json",
    "history/daily_reports/*",
    "snapshots/snapshot_*",
)


def runtime_artifact_patterns() -> list[str]:
    return list(DEFAULT_RUNTIME_ARTIFACT_PATTERNS)


def find_runtime_artifacts(root: Path) -> list[Path]:
    root = Path(root)
    found: list[Path] = []
    seen: set[str] = set()

    for pattern in DEFAULT_RUNTIME_ARTIFACT_PATTERNS:
        for path in sorted(root.glob(pattern)):
            key = path.as_posix()
            if key not in seen and path.exists():
                seen.add(key)
                found.append(path)

    return found
