"""Verify staged/tracked file hygiene and source/schema integrity without printing secrets."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from core.corpus import load_dataset
    from core.schemas import ScholarshipAnswer

    shell = (ROOT / "backend/entrypoint.sh").read_bytes()
    if not shell.startswith(b"#!/bin/sh\n") or b"\r" in shell:
        raise ValueError("Docker entrypoint must be nonempty and use Unix line endings.")
    dataset = load_dataset()
    schema = json.loads(
        (ROOT / "backend/schemas/assistant_response_schema.json").read_text(encoding="utf-8")
    )
    if schema != ScholarshipAnswer.model_json_schema():
        raise ValueError("Generated assistant response schema is out of date.")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    failures = []
    patterns = [
        re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
        re.compile(r"sk-[0-9A-Za-z_-]{24,}"),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    for name in filter(None, tracked):
        path = ROOT / name
        if name.endswith(".env") or any(
            part in name.split("/") for part in ("node_modules", ".venv", "__pycache__", "var")
        ):
            failures.append(name)
            continue
        if path.is_file():
            contents = path.read_text(encoding="utf-8", errors="replace")
            if any(pattern.search(contents) for pattern in patterns):
                failures.append(name)
    if failures:
        print("Repository hygiene check failed for:", ", ".join(failures))
        return 1
    print(f"Repository hygiene passed for {len(list(filter(None, tracked)))} staged/tracked files.")
    print(f"Corpus provenance and schema integrity passed for {len(dataset['schemes'])} records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
