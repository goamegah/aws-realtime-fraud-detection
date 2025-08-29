import subprocess
from pathlib import Path
from typing import Optional

from .config import ROOT_DIR


def run_build(python_exe: str = "python3") -> None:
    # Install build if missing is left to user; Makefile provides helper.
    subprocess.run([python_exe, "-m", "build"], cwd=str(ROOT_DIR), check=True)


def find_latest_wheel(dist_dir: Path) -> Optional[Path]:
    if not dist_dir.exists():
        return None
    wheels = sorted(dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return wheels[0] if wheels else None
