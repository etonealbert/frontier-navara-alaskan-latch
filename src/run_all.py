"""Полный цикл V01 одной командой: построение → проверки → виды → чертёж → сопоставление с фото.

Запуск: .venv/bin/python src/run_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
STEPS = ["model.py", "validate.py", "render.py", "drawing.py", "compare_photos.py"]


def main():
    for step in STEPS:
        print(f"=== {step}", flush=True)
        result = subprocess.run([sys.executable, str(SRC / step)], cwd=SRC.parent)
        if result.returncode != 0:
            sys.exit(f"{step} failed with exit code {result.returncode}")
    print("=== done")


if __name__ == "__main__":
    main()
