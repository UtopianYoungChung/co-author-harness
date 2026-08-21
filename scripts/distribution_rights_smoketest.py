#!/usr/bin/env python3
"""Regression tests for forward-looking distribution-rights enforcement."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "distribution-rights-check.py"
REGISTRY = ROOT / "references" / "distribution_rights.json"

# Independent deletion-time pins. Editing the registry and checker together
# must not silently erase the historical forbidden-content baseline.
REQUIRED_REMOVED_SHA256 = {
    "020995c571f96fead7ba06786c5701d3d252780bd5d4d63dbc7c63d1d74aa418",
    "d0834f8e120394d6f60cc9814631f5013185d7491a88af95e7c95bdc04ec00b0",
    "801bd509d3c9cee5796eecd5663b585e98b159c25b86daab439f31152377ed2e",
    "d24a186b2f118076c63ed47396738ce0ad95008907d87b455ffab9dcb3013812",
    "5bed11a17615600db8b195e8b278ea7b5b65aa3ae94dad2fa680bac0df479895",
    "f3e2a0e114c76120aaed8e9de872873c59c5e1a94ca2bca619a7dafb4a9967ec",
    "16523ad1e4726da6bf4d0fa4ea2a58d8cca93df83fdbe5b427264ee6f30e319b",
    "f7568eb834f887a0ebc9432f1290c31e53ad2ed0f03305b1988a7c54205a01cd",
    "87b57704b4a689b0c63ef3b0e2cee7cebb2429a721499f2051415585b0fb2f52",
}
REQUIRED_REMOVED_TEXT_SHA256 = {
    "685a8606cfc26798c39af44d3e44f14afa5f4b1dabcc6a59eb869b595a927e37",
    "d375b442c34a06633f3f62129984131d9d22f6b35f9dc34413259d575b44e35a",
    "3f6565e0a06ff3ae24a43578ad721873a3171eeae63e05ce9e1037702d29c723",
    "944d6d28ad214e733a9d7daa303278e980d066da3e6cf728ba5403c30e87e1d7",
    "9544a1cf28845e47d0ef57921c91bf444d8f38564529015f9c153b50d91178da",
    "9b903ea153ee2ce4cc623ac9da2f637540c2ca7ed067b471747398de53edc129",
    "7248b927e9f2706057d0c2c14879aeabf86d894bd2998e7c85c39ee60445b3e6",
    "f7ea6d34b26143f44a1f467e4e492ab59b0f47e68e83c19227c953120f93a43a",
    "20fa6f71a2d81370a7e5a8970e6f8c3c35ff68d1c9b8c396fb6f76dc8286b92c",
    "a1221b37e47ed136668251d87bad48dffdc272fb043e5e1c8f5f03d591b4d459",
    "1ada7b82353a703f3b7599f8918b4625aa1687c7ef63a98f8c80bafd7985c5ff",
    "2999548667df992bb54f7f6b9487caaaab260fdd5badf604b4dc45455fd9cefd",
    "02133af5cc3324f25c3879e4c42232834565a3b97316d48175e3da4b137ea5fc",
    "68b795eaecb7c831016cf243a603c1d1e1375f97845210e9c6b4437ac8274427",
    "4fc3b58533811938da9b0ece1ffdb83b0f566771f98c4b9ba5de974d1011e933",
}


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8", newline="\n")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def base_registry(forbidden_bytes: bytes = b"removed synthetic source bytes") -> dict:
    replacement = b"synthetic replacement\n"
    return {
        "schema": "coauthor-distribution-rights/v1",
        "package_license": "MIT",
        "history_scope": "current-tree-and-future-artifacts-only",
        "notice_path": "THIRD_PARTY_NOTICES.md",
        "local_only_roots": ["references/resources/local/"],
        "materials": [
            {
                "id": "synthetic-removed-source",
                "disposition": "excluded",
                "historical_paths": ["references/resources/removed.txt"],
                "forbidden_sha256": [sha256(forbidden_bytes)],
                "forbidden_text_sha256": [sha256(b"removed synthetic passage")],
                "replacement_paths": ["references/guideline.md"],
                "replacement_sha256": {
                    "references/guideline.md": sha256(replacement)
                },
            }
        ],
        "enforcement_surfaces": {
            "AGENTS.md": "python scripts/distribution-rights-check.py",
            ".github/workflows/structural-checks.yml": "distribution-rights-check.py",
            "scripts/release-gate.sh": "distribution-rights-check.py",
            "scripts/analysis/fixture_runner.py": "scripts/distribution_rights_smoketest.py",
        },
    }


def fixture(base: Path, registry: dict | None = None) -> Path:
    root = base / "plugin"
    data = copy.deepcopy(registry or base_registry())
    write(root / ".claude-plugin/plugin.json", json.dumps({
        "name": "fixture", "version": "1.0.0", "description": "fixture",
        "keywords": [], "license": "MIT",
    }) + "\n")
    write(root / "references/distribution_rights.json",
          json.dumps(data, indent=2) + "\n")
    write(root / "references/guideline.md", "synthetic replacement\n")
    write(root / "THIRD_PARTY_NOTICES.md",
          "# Third-party notices\n\nScope: current tree and future artifacts only.\n")
    write(root / ".gitignore", "references/resources/local/\n")
    for path, needle in data["enforcement_surfaces"].items():
        write(root / path, f"{needle}\n")
    return root


def run(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(CHECKER), "--plugin-root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return proc.returncode, proc.stdout + proc.stderr


def require_block(root: Path, *needles: str) -> None:
    rc, output = run(root)
    assert rc == 1, f"expected blocker, rc={rc}: {output}"
    blockers = [line.lower() for line in output.splitlines() if "[blocker]" in line.lower()]
    assert any(all(needle.lower() in line for needle in needles) for line in blockers), output


def main() -> int:
    assert CHECKER.is_file(), f"missing enforcement entrypoint: {CHECKER}"
    assert REGISTRY.is_file(), f"missing rights registry: {REGISTRY}"

    real = json.loads(REGISTRY.read_text(encoding="utf-8"))
    observed = {
        digest
        for material in real.get("materials", [])
        for digest in material.get("forbidden_sha256", [])
    }
    assert observed == REQUIRED_REMOVED_SHA256, (
        "deletion-time forbidden hash baseline drifted: "
        f"missing={sorted(REQUIRED_REMOVED_SHA256 - observed)} "
        f"extra={sorted(observed - REQUIRED_REMOVED_SHA256)}"
    )
    observed_text = {
        digest
        for material in real.get("materials", [])
        for digest in material.get("forbidden_text_sha256", [])
    }
    assert observed_text == REQUIRED_REMOVED_TEXT_SHA256, (
        "deletion-time forbidden text baseline drifted: "
        f"missing={sorted(REQUIRED_REMOVED_TEXT_SHA256 - observed_text)} "
        f"extra={sorted(observed_text - REQUIRED_REMOVED_TEXT_SHA256)}"
    )

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        rc, output = run(root)
        assert rc == 0, output

    forbidden = b"removed synthetic source bytes"
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        write(root / "renamed/copy.bin", forbidden)
        require_block(root, "forbidden", "sha256", "renamed/copy.bin")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        write(root / "references/resources/removed.txt", forbidden)
        require_block(root, "forbidden", "sha256", "removed.txt")

    for prefix in ("> ", "- ", "1. ", "## "):
        with tempfile.TemporaryDirectory() as td:
            root = fixture(Path(td))
            write(root / "renamed/partial.md",
                  f"{prefix}removed synthetic passage\n")
            require_block(root, "forbidden", "text", "partial.md")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        (root / "references/guideline.md").unlink()
        require_block(root, "replacement", "missing")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        write(root / "references/guideline.md", "drifted replacement\n")
        require_block(root, "replacement", "sha256")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
        manifest["license"] = "UNLICENSED"
        write(root / ".claude-plugin/plugin.json", json.dumps(manifest) + "\n")
        require_block(root, "license", "UNLICENSED", "MIT")

    with tempfile.TemporaryDirectory() as td:
        data = base_registry()
        data["materials"][0]["disposition"] = "unknown"
        require_block(fixture(Path(td), data), "disposition", "unknown")

    with tempfile.TemporaryDirectory() as td:
        data = base_registry()
        data["materials"][0]["disposition"] = "replaced-with-synthetic"
        data["materials"][0]["historical_paths"].append("docs/removed-plan.md")
        root = fixture(Path(td), data)
        write(root / "docs/removed-plan.md", "new non-matching content\n")
        require_block(root, "historical", "remain absent", "removed-plan.md")

    with tempfile.TemporaryDirectory() as td:
        data = base_registry()
        data["materials"][0]["forbidden_sha256"] = []
        require_block(fixture(Path(td), data), "forbidden_sha256", "non-empty")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        write(root / "AGENTS.md", "# missing enforcement wiring\n")
        require_block(root, "enforcement", "AGENTS.md")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        write(root / ".gitignore", "# local sources accidentally trackable\n")
        require_block(root, "local-only", "gitignore")

    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        write(root / "references/resources/local/private-source.txt", "local only\n")
        subprocess.run(["git", "init", "--quiet", str(root)], check=True,
                       capture_output=True)
        subprocess.run(
            ["git", "-C", str(root), "add", "-f",
             "references/resources/local/private-source.txt"],
            check=True, capture_output=True,
        )
        require_block(root, "local-only", "distributable", "private-source.txt")

    print("PASS: distribution rights are fail-closed for future package bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
