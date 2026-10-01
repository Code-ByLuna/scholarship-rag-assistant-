"""Capture installed versions for the runtime dependency closure, excluding unrelated packages."""

from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def main():
    pending = []
    platform_lines = []
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        req = Requirement(line)
        if req.marker and not req.marker.evaluate():
            platform_lines.append(line)
        else:
            pending.append(req.name)
    pinned = {}
    while pending:
        name = canonicalize_name(pending.pop())
        if name in pinned:
            continue
        try:
            installed = distribution(name)
        except PackageNotFoundError:
            raise RuntimeError(f"Required installed package missing: {name}") from None
        pinned[name] = installed.version
        for dependency in installed.requires or []:
            req = Requirement(dependency)
            if not req.marker or req.marker.evaluate({"extra": ""}):
                pending.append(req.name)
    text = "# Tested Windows/Python 3.10 dependency closure; Linux-specific dependencies are resolved on Linux.\n"
    text += "\n".join(f"{name}=={version}" for name, version in sorted(pinned.items()))
    text += "\n" + "\n".join(platform_lines) + "\n"
    (ROOT / "requirements.lock").write_text(text, encoding="utf-8")
    print(f"Captured {len(pinned)} installed package versions.")


if __name__ == "__main__":
    main()
