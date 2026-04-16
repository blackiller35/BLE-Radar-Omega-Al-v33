from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)

TARGET_DIRS = ["state", "history", "reports"]


def snapshot_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def create_snapshot():
    stamp = snapshot_stamp()
    base = SNAP_DIR / f"snapshot_{stamp}"
    base.mkdir(parents=True, exist_ok=True)

    copied = []
    for rel in TARGET_DIRS:
        src = ROOT / rel
        dst = base / rel
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            copied.append(rel)

    return {"stamp": stamp, "path": base, "copied": copied}


def list_snapshots():
    snaps = sorted(SNAP_DIR.glob("snapshot_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return snaps


def restore_snapshot(path_str: str):
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(path)

    restored = []
    for rel in TARGET_DIRS:
        src = path / rel
        dst = ROOT / rel
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            restored.append(rel)

    return {"path": path, "restored": restored}
