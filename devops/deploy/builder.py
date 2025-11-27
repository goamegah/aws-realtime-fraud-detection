import subprocess
from pathlib import Path
from typing import Optional

from .config import ROOT_DIR


def run_build() -> None:
    # Install build if missing is left to user; Makefile provides helper.
    import sys
    subprocess.run([sys.executable, "-m", "build"], cwd=str(ROOT_DIR), check=True)


def find_latest_wheel(dist_dir: Path) -> Optional[Path]:
    if not dist_dir.exists():
        return None
    wheels = sorted(dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return wheels[0] if wheels else None
