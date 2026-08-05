#!/usr/bin/env python3
"""Generate SBOM.cyclonedx.json from pip-licenses and license-checker output."""

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "SBOM.cyclonedx.json"


def _run(cmd: list[str]) -> str:
    return subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def _backend_components() -> list[dict]:
    if shutil.which("pip-licenses") is None:
        sys.exit(
            "pip-licenses が見つかりません。`pip install pip-licenses` を実行してください。"
        )
    raw = json.loads(_run(["pip-licenses", "--format=json", "--with-system"]))
    components = []
    for item in raw:
        license_name = item.get("License") or item.get("License-Expression") or "Unknown"
        component = {
            "type": "library",
            "name": item["Name"],
            "version": item.get("Version", ""),
        }
        if license_name and license_name != "UNKNOWN":
            component["licenses"] = [{"license": {"name": license_name}}]
        components.append(component)
    return components


def _frontend_components() -> list[dict]:
    local_license_checker = (
        ROOT / "frontend" / "node_modules" / ".bin" / "license-checker"
    )
    license_checker = (
        str(local_license_checker)
        if local_license_checker.exists()
        else shutil.which("license-checker")
    )
    if license_checker is None:
        sys.exit(
            "license-checker が見つかりません。"
            "`npm install --no-save license-checker` を実行してください。"
        )
    raw = json.loads(_run([license_checker, "--json"]))
    components = []
    for full_name, info in raw.items():
        if "@" in full_name:
            name, version = full_name.rsplit("@", 1)
        else:
            name, version = full_name, ""
        licenses = info.get("licenses") or "Unknown"
        if isinstance(licenses, str):
            licenses = [licenses]
        component = {"type": "library", "name": name, "version": version}
        if licenses:
            component["licenses"] = [
                {"license": {"name": lic}} for lic in licenses if lic != "UNKNOWN"
            ]
        components.append(component)
    return components


def main() -> None:
    components = _backend_components() + _frontend_components()
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:open-bim-platform-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "component": {
                "type": "application",
                "name": "open-bim-platform",
                "version": "0.1.0",
            },
        },
        "components": components,
    }
    OUTPUT.write_text(json.dumps(bom, indent=2, ensure_ascii=False) + "\n")
    print(f"✅ SBOM 生成: {OUTPUT} ({len(components)} components)")


if __name__ == "__main__":
    main()
