"""Run with system Python from the server checkout; secrets are entered without echo."""
import getpass
import os
import re
import tempfile
from pathlib import Path


def main():
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file() or env_path.is_symlink():
        raise SystemExit("Expected an existing regular .env in the deployment directory.")
    ak = getpass.getpass("TOS Access Key ID (hidden): ").strip()
    sk = getpass.getpass("TOS Secret Access Key (hidden): ").strip()
    if not all(re.fullmatch(r"[A-Za-z0-9/+=_-]+", value) for value in (ak, sk)):
        raise SystemExit("Empty or invalid credential. No configuration changed.")
    values = {
        "STORAGE_BACKEND": "tos",
        "TOS_BUCKET": "ued-zhiku",
        "TOS_REGION": "cn-shanghai",
        "TOS_ENDPOINT": "https://tos-cn-shanghai.volces.com",
        "TOS_PREFIX": "piancton",
        "TOS_ACCESS_KEY_ID": ak,
        "TOS_SECRET_ACCESS_KEY": sk,
    }
    lines = []
    for line in env_path.read_text().splitlines():
        key = line.split("=", 1)[0].strip().removeprefix("export ").strip()
        if key not in values:
            lines.append(line)
    lines.extend(f"{key}={value}" for key, value in values.items())
    with tempfile.NamedTemporaryFile(mode="w", dir=env_path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write("\n".join(lines) + "\n")
    try:
        temporary.chmod(0o600)
        os.replace(temporary, env_path)
    finally:
        temporary.unlink(missing_ok=True)
    print("Saved TOS configuration to .env (mode 600). Other settings preserved.")


if __name__ == "__main__":
    main()
