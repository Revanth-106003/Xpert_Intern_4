"""Pre-flight check executed by run.bat / run.sh before the UI starts.

* initialises the SQLite database
* verifies the configured LLM provider (without silently switching providers)
* prints exact instructions for anything missing

Exit code is always 0 so the UI still starts and can show the same guidance.
"""
from __future__ import annotations

import sys

from agent import LLMClient
from config import APP_NAME, load_settings
from database import Database


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    settings = load_settings()
    print(f"\n  {APP_NAME} - pre-flight check")
    print("  " + "-" * 52)

    db = Database(settings.database_path)
    print(f"  [OK]   SQLite database ready: {db.path}")

    status = LLMClient(settings).describe_status()
    label = f"{settings.llm_provider} / {settings.active_model}"
    if status["ok"]:
        print(f"  [OK]   LLM provider configured: {label}")
    else:
        print(f"  [WARN] LLM provider '{label}' is not ready")
        print(f"         {status['message']}")
        if status.get("hint"):
            print(f"         Fix: {status['hint']}")
        print("         The app will still start; generation will report this error until it is fixed.")
    print("  " + "-" * 52 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
