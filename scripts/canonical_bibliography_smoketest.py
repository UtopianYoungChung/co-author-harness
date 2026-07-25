#!/usr/bin/env python3
"""Focused C2 red boundary for canonical bibliography provenance."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from c2_evidence_fixture_support import ASSET_ROOT, build_activation_fixture
import canonical_bibliography as bibliography_module


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "product_assurance.py"
BIBLIOGRAPHY_SCRIPT = ROOT / "scripts" / "canonical_bibliography.py"
PRODUCT_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT / "references" / "schemas" / "product_assurance.schema.json").read_text(
        encoding="utf-8"
    )
))
V3_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT / "references" / "schemas" / "centroid_semantic_execution.v3.schema.json").read_text(
        encoding="utf-8"
    )
))
BIBLIOGRAPHY_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT / "references" / "schemas" / "canonical_bibliography_snapshot.schema.json").read_text(
        encoding="utf-8"
    )
))
BLOCKER_VALIDATOR = Draft202012Validator(json.loads(
    (ROOT / "references" / "schemas" / "canonical_bibliography_blocker.schema.json").read_text(
        encoding="utf-8"
    )
))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    artifact: Path,
    receipt: Path,
    output: Path,
    project_root: Path,
    wiki_root: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "build",
            "--artifact",
            str(artifact),
            "--semantic-receipt",
            str(receipt),
            "--project-root",
            str(project_root),
            "--wiki-root",
            str(wiki_root),
            "--out",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def refusal_codes(output: Path) -> set[str]:
    if not output.is_file():
        return set()
    payload = json.loads(output.read_text(encoding="utf-8"))
    PRODUCT_VALIDATOR.validate(payload)
    codes: set[str] = set()
    reason = payload.get("reason_code")
    if isinstance(reason, str):
        codes.add(reason)
    for row in payload.get("findings", []):
        if isinstance(row, dict) and isinstance(row.get("code"), str):
            codes.add(row["code"])
    return codes


def main() -> int:
    intended_red: list[str] = []
    with tempfile.TemporaryDirectory(prefix="coauthor-bibliography-c2-") as td:
        root = Path(td)
        fixture = build_activation_fixture(root / "activation")
        V3_VALIDATOR.validate(json.loads(fixture.receipt.read_text(encoding="utf-8")))
        BIBLIOGRAPHY_VALIDATOR.validate(json.loads(
            fixture.bibliography_snapshot.read_text(encoding="utf-8")
        ))
        snapshot = json.loads(fixture.bibliography_snapshot.read_text(encoding="utf-8"))
        publication_manifest = json.loads(
            fixture.bibliography_manifest.read_text(encoding="utf-8")
        )
        publication_marker = json.loads(
            fixture.bibliography_marker.read_text(encoding="utf-8")
        )
        assert snapshot["publication"]["mode"] == "committed"
        assert publication_marker["state"] == "committed"
        assert (
            publication_marker["final_output_hashes"]
            == publication_manifest["intended_outputs"]
        )
        assert snapshot["sources"][0]["lookup_key"] == "fixture-centroid-alias"
        assert snapshot["sources"][0]["redirect_chain"] == [
            "fixture-centroid-evidence"
        ]
        assert fixture.bibliography_marker.stat().st_mtime_ns >= max(
            fixture.bibliography_snapshot.stat().st_mtime_ns,
            fixture.bibliography_manifest.stat().st_mtime_ns,
        )

        blocked = subprocess.run(
            [
                sys.executable,
                str(BIBLIOGRAPHY_SCRIPT),
                "--project-root", str(fixture.root),
                "--project-manifest", str(fixture.project_manifest),
                "--wiki-root", str(fixture.wiki_root),
                "--wiki-manifest", str(fixture.wiki_root / "manifest.json"),
                "--policy", str(fixture.wiki_root / "policy.json"),
                "--source-key", "missing-source-key",
                "--snapshot-id", "blocked-control",
                "--out", str(fixture.root / "blocked-bibliography.json"),
                "--manifest-out", str(fixture.root / "blocked-manifest.json"),
                "--commit-marker-out", str(fixture.root / "blocked-marker.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert blocked.returncode == 4
        blocked_payload = json.loads(blocked.stderr)
        BLOCKER_VALIDATOR.validate(blocked_payload)
        assert blocked_payload["reason_code"] == "CITATION-REDIRECT-INVALID"
        assert not (fixture.root / "blocked-bibliography.json").exists()
        assert not (fixture.root / "blocked-manifest.json").exists()
        assert not (fixture.root / "blocked-marker.json").exists()

        race_project = root / "redirect-race-project"
        race_project.mkdir(parents=True)
        shutil.copyfile(ASSET_ROOT / "miniature.pdf", race_project / "miniature.pdf")
        race_manifest = race_project / "manifest.json"
        race_manifest.write_text(
            json.dumps({
                "schema_version": "1.0.0",
                "identity": "redirect-race-project",
                "admitted_sources": [{
                    "path": "miniature.pdf",
                    "sha256": sha(race_project / "miniature.pdf"),
                }],
            }, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        race_wiki = root / "redirect-race-wiki"
        shutil.copytree(ASSET_ROOT / "wiki", race_wiki)
        race_out = race_project / "snapshot.json"
        race_publication_manifest = race_project / "publication-manifest.json"
        race_marker = race_project / "publication-marker.json"
        original_publish = bibliography_module.publish_committed

        def mutate_redirect_before_claim(**kwargs):
            redirect = race_wiki / "wiki" / "sources" / "c2-redirect.md"
            redirect.write_text(
                redirect.read_text(encoding="utf-8").replace(
                    "redirect_to: fixture-centroid-evidence",
                    "redirect_to: fixture-argument-evidence",
                ),
                encoding="utf-8",
                newline="\n",
            )
            return original_publish(**kwargs)

        bibliography_module.publish_committed = mutate_redirect_before_claim
        try:
            bibliography_module.publish_bibliography(
                project_root=race_project,
                project_manifest=race_manifest,
                wiki_root=race_wiki,
                wiki_manifest=race_wiki / "manifest.json",
                policy=race_wiki / "policy.json",
                source_keys=["fixture-centroid-alias"],
                snapshot_id="redirect-race",
                out=race_out,
                manifest_out=race_publication_manifest,
                commit_marker_out=race_marker,
            )
        except bibliography_module.EvidencePublicationError as exc:
            assert "inventory changed under claim" in str(exc)
        else:
            raise AssertionError("redirect inventory drift was committed")
        finally:
            bibliography_module.publish_committed = original_publish
        assert not race_out.exists()
        assert not race_publication_manifest.exists()
        assert not race_marker.exists()
        benign_output = root / "benign-report.json"
        benign = run(
            fixture.artifact,
            fixture.receipt,
            benign_output,
            fixture.root,
            fixture.wiki_root,
        )
        assert benign.returncode == 0, benign.stdout + benign.stderr
        benign_payload = json.loads(benign_output.read_text(encoding="utf-8"))
        PRODUCT_VALIDATOR.validate(benign_payload)
        assert benign_payload["status"] == "passed"
        baseline_receipt_sha = sha(fixture.receipt)
        stable = {
            key: benign_payload[key]
            for key in (
                "status",
                "artifact",
                "corpus_extract_sha256",
                "dimensions",
                "findings",
                "adjudications",
            )
        }

        def negative_case(
            label: str,
            expected_code: str,
            *,
            bibliography_change=None,
            receipt_change=None,
            fixture_change=None,
        ) -> None:
            fixture.reset()
            if bibliography_change is not None:
                fixture.mutate_bibliography(bibliography_change)
            if receipt_change is not None:
                fixture.mutate_receipt(receipt_change)
            if fixture_change is not None:
                fixture_change()
            attacked_sha = sha(fixture.receipt)
            assert attacked_sha != baseline_receipt_sha
            output = root / ("-".join(label.split()) + ".json")
            result = run(
                fixture.artifact,
                fixture.receipt,
                output,
                fixture.root,
                fixture.wiki_root,
            )
            if result.returncode == 0:
                payload = json.loads(output.read_text(encoding="utf-8"))
                assert {key: payload[key] for key in stable} == stable
                assert payload["semantic_receipt"] == {
                    "path": str(fixture.receipt.resolve()),
                    "sha256": attacked_sha,
                }
            actual_codes = refusal_codes(output)
            if result.returncode == 0 or expected_code not in actual_codes:
                intended_red.append(
                    f"{label}: expected nonzero/{expected_code}, "
                    f"actual rc={result.returncode} codes={sorted(actual_codes)}"
                )

        negative_case(
            "metadata missing",
            "CITATION-METADATA-MISSING",
            bibliography_change=lambda value: value["sources"][0].pop("title"),
        )
        negative_case(
            "invented redirect chain",
            "CITATION-REDIRECT-INVALID",
            bibliography_change=lambda value: value["sources"][0].update({
                "redirect_chain": ["missing-source-key"]
            }),
        )
        negative_case(
            "redirect escape",
            "CITATION-REDIRECT-INVALID",
            bibliography_change=lambda value: value["sources"][0].update(
                {"redirect_chain": ["../../outside-source"]}
            ),
        )
        negative_case(
            "alias collision",
            "CITATION-BIBLIOGRAPHY-AMBIGUOUS",
            bibliography_change=lambda value: value["sources"][1]["aliases"].append(
                "c2-centroid"
            ),
        )
        negative_case(
            "malformed snapshot",
            "CITATION-SNAPSHOT-INVALID",
            bibliography_change=lambda value: value.update({"sources": {}}),
        )
        negative_case(
            "internally rebuilt snapshot",
            "CITATION-SNAPSHOT-INVALID",
            fixture_change=fixture.remove_bibliography_commit_marker,
        )
        negative_case(
            "canonical page bytes changed",
            "CITATION-SNAPSHOT-STALE",
            bibliography_change=lambda value: value["sources"][0][
                "canonical_page"
            ].update({"sha256": "0" * 64}),
        )
        negative_case(
            "source bytes changed",
            "CITATION-SNAPSHOT-STALE",
            bibliography_change=lambda value: value["sources"][0]["source"].update(
                {"sha256": "0" * 64}
            ),
        )
        negative_case(
            "wiki root substituted",
            "CITATION-ROOT-MISMATCH",
            bibliography_change=lambda value: value["wiki_root"].update(
                {"identity": "c2-lookalike-wiki"}
            ),
        )
        negative_case(
            "consistent page source snapshot substitution",
            "CITATION-ROOT-MISMATCH",
            fixture_change=fixture.substitute_bibliography_root,
        )
        negative_case(
            "canonical title changed",
            "CITATION-IDENTITY-MISMATCH",
            bibliography_change=lambda value: value["sources"][0].update(
                {"title": "Fixture argument evidence"}
            ),
        )
        negative_case(
            "source loc same basename changed",
            "CITATION-IDENTITY-MISMATCH",
            bibliography_change=lambda value: value["sources"][0].update(
                {"source_loc": "other/miniature.pdf"}
            ),
        )
        negative_case(
            "cited subset suffix changed",
            "CITATION-IDENTITY-MISMATCH",
            receipt_change=lambda value: value["passages"][0]["citation"].update(
                {"label": "2026a"}
            ),
        )
        negative_case(
            "manuscript bibliography identity changed",
            "CITATION-IDENTITY-MISMATCH",
            fixture_change=lambda: fixture.mutate_artifact(
                lambda text: text.replace(
                    "Fixture centroid evidence.",
                    "Different bibliography identity.",
                )
            ),
        )
        negative_case(
            "manuscript bibliography authors changed",
            "CITATION-IDENTITY-MISMATCH",
            fixture_change=lambda: fixture.mutate_artifact(
                lambda text: text.replace("Fixture, C.", "Wrong, X.", 1)
            ),
        )

    if intended_red:
        raise AssertionError(
            "C2 intended-red canonical-bibliography regressions:\n- "
            + "\n- ".join(intended_red)
        )
    print("canonical_bibliography_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
