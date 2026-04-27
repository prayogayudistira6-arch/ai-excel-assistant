from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    app_path = project_root / "app" / "ui" / "streamlit_app.py"
    data_output = project_root / "data" / "output"
    data_output.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "localhost",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    command.extend(sys.argv[1:])

    print("Starting AI Spreadsheet Assistant web app...")
    print("URL: http://localhost:8501")
    print("Stop with Ctrl+C")
    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    return subprocess.call(command, cwd=project_root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
