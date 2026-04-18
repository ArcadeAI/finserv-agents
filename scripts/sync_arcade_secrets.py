#!/usr/bin/env python3
"""
Sync required FinServ secrets from the local .env file into Arcade.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import sys

from dotenv import dotenv_values

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
REQUIRED_SECRETS = ("REDIS_URL",)
OPTIONAL_RUNTIME_KEYS = ("ARCADE_GATEWAY_URL", "ARCADE_API_KEY", "ARCADE_USER_ID", "ANTHROPIC_API_KEY")


def require_arcade_login() -> None:
    try:
        subprocess.run(
            ["arcade", "whoami"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Arcade CLI is not installed. Run `make install` first.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        message = stderr or "Arcade CLI is not logged in. Run `arcade login` before `make deploy`."
        raise RuntimeError(message) from exc


def main() -> None:
    if not ENV_PATH.exists():
        raise RuntimeError(".env is missing. Copy .env.example and configure it before deployment.")

    require_arcade_login()

    env_values = dotenv_values(ENV_PATH)
    for key in REQUIRED_SECRETS:
        value = env_values.get(key, "")
        if not value:
            raise RuntimeError(f"{key} is missing in .env. Run setup first and fill the required values.")

        subprocess.run(
            ["arcade", "secret", "set", f"{key}={value}"],
            check=True,
        )

    missing_runtime_keys = [key for key in OPTIONAL_RUNTIME_KEYS if not env_values.get(key, "")]
    if missing_runtime_keys:
        print(
            "Warning: live app env is still incomplete. "
            f"Set {', '.join(missing_runtime_keys)} in .env before testing chat.",
            file=sys.stderr,
        )

    print("Arcade secrets synchronized.")


if __name__ == "__main__":
    main()
