"""Retrieve the original UCI steel energy archive, preserving source bytes and attribution."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import requests

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip"


def main():
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "steel_energy.zip"
    if not archive.exists():
        temporary = archive.with_suffix(".partial")
        with requests.get(URL, stream=True, timeout=(30, 120)) as response:
            response.raise_for_status()
            with temporary.open("wb") as out:
                for chunk in response.iter_content(1024 * 1024):
                    out.write(chunk)
        temporary.replace(archive)
    with ZipFile(archive) as zipped:
        if any(
            not (raw / member).resolve().is_relative_to(raw.resolve())
            for member in zipped.namelist()
        ):
            raise ValueError("Unsafe archive path")
        zipped.extractall(raw)
    previous = ROOT / "reports/provenance.json"
    retrieved = json.loads(previous.read_text()).get("retrieved_utc") if previous.exists() else None
    files = []
    for path in sorted(raw.glob("*")):
        if path.is_file() and path.name != ".gitkeep":
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            files.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                }
            )
    metadata = {
        "source_url": URL,
        "dataset_url": "https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption",
        "doi": "10.24432/C52G8C",
        "license": "CC BY 4.0",
        "retrieved_utc": retrieved or datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    previous.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
