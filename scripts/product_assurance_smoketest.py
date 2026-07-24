#!/usr/bin/env python3
"""Hermetic regressions for the product-assurance kernel."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "product_assurance.py"
RUN_ALL = ROOT / "scripts" / "audit" / "run_all.py"
SOURCE_EXTRACT = ROOT / "scripts" / "source_extract.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha(path)}


def run(manuscript: Path, receipt: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "build", "--artifact", str(manuscript),
         "--semantic-receipt", str(receipt), "--out", str(output)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def write_receipt(path: Path, manuscript: Path, source_a: Path, extract_a: Path,
                  source_b: Path, extract_b: Path, *, quote: str,
                  label: str = "1994a") -> None:
    payload = {
        "schema_version": "2.0.0",
        "receipt_type": "centroid_semantic_execution",
        "target": "M4",
        "phase": "evaluation",
        "role": "evaluator",
        "actor_id": "eval-1",
        "dispatch_id": "dispatch-eval-1",
        "artifact": binding(manuscript),
        "centroid_packet": {"path": str(path.resolve()), "sha256": "0" * 64},
        "generation_envelope": {"path": str(path.resolve()), "sha256": "0" * 64},
        "adjudications": [],
        "passages": [
            {
                "source_key": "yu-mylopoulos-1994-understanding-why",
                "use_scope": "surface",
                "source": binding(source_a),
                "locator": "p. 3",
                "extract": binding(extract_a),
                "extraction": {"method": "text-direct", "tool": "utf-8", "canonical": True},
                "quote": quote,
                "citation": {
                    "authors": ["Yu, E.", "Mylopoulos, J."], "year": 1994,
                    "title": "Understanding why in software process modelling",
                    "label": label,
                },
                "use": "Register and quotation evidence.",
            },
            {
                "source_key": "yu-mylopoulos-1994-modelling-strategic-actors",
                "use_scope": "surface",
                "source": binding(source_b),
                "locator": "p. 1",
                "extract": binding(extract_b),
                "extraction": {"method": "text-direct", "tool": "utf-8", "canonical": True},
                "quote": "social actors depend on each other",
                "citation": {
                    "authors": ["Yu, E.", "Mylopoulos, J."], "year": 1994,
                    "title": "Modelling strategic actor relationships",
                    "label": "1994b",
                },
                "use": "Register evidence.",
            },
        ],
        "semantic_assessment": {
            "summary": "independent semantic review", "strengths": [],
            "deviations": [], "warrant_limits": [], "actionable_findings": [],
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    # Self-bindings above are deliberately ignored by this kernel; draft
    # governance owns cross-envelope identity and exact packet verification.


def main() -> int:
    assert SCRIPT.is_file(), "product assurance kernel has not been implemented"
    with tempfile.TemporaryDirectory(prefix="product-assurance-") as td:
        root = Path(td)
        source_a = root / "why.txt"; extract_a = root / "why.extract.txt"
        source_b = root / "actors.txt"; extract_b = root / "actors.extract.txt"
        text_a = "requirements models reveal the whys behind the whats and hows"
        text_b = "processes involve social actors depend on each other for goals"
        for path, text in ((source_a, text_a), (extract_a, text_a),
                           (source_b, text_b), (extract_b, text_b)):
            path.write_text(text + "\n", encoding="utf-8")
        adapter_text = root / "adapter.extract.txt"
        adapter_receipt = root / "adapter.extract.json"
        adapter = subprocess.run(
            [sys.executable, str(SOURCE_EXTRACT), "--source", str(source_a),
             "--text-out", str(adapter_text), "--receipt-out", str(adapter_receipt)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert adapter.returncode == 0, adapter.stdout + adapter.stderr
        adapter_payload = json.loads(adapter_receipt.read_text(encoding="utf-8"))
        assert adapter_payload["extraction"] == {
            "method": "text-direct", "tool": "utf-8", "canonical": True,
        }

        good = root / "good.md"
        good.write_text(
            "# Abstract\n\nThe model reveals \"the whys behind the whats and hows\" "
            "(Yu & Mylopoulos, 1994a).\n\n# Body\n\nSocial actors depend on each other "
            "(Yu & Mylopoulos, 1994b).\n\n# References\n\n"
            "Yu, E., & Mylopoulos, J. (1994a). Understanding why in software process modelling.\n"
            "Yu, E., & Mylopoulos, J. (1994b). Modelling strategic actor relationships.\n",
            encoding="utf-8")
        receipt = root / "receipt.json"; report = root / "report.json"
        write_receipt(receipt, good, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows")
        result = run(good, receipt, report)
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert payload["status"] == "passed"
        assert payload["dimensions"]["grounding"] == "passed"
        assert payload["dimensions"]["register"] == "passed"

        wrong_quote = root / "wrong-quote.json"
        write_receipt(wrong_quote, good, source_a, extract_a, source_b, extract_b,
                      quote="words absent from the canonical extract")
        result = run(good, wrong_quote, root / "wrong-quote-report.json")
        assert result.returncode == 2 and "QUOTE-NOT-IN-EXTRACT" in result.stdout

        wrong_label = root / "wrong-label.json"
        write_receipt(wrong_label, good, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows", label="1994b")
        result = run(good, wrong_label, root / "wrong-label-report.json")
        assert result.returncode == 2 and "CITATION-SAME-YEAR" in result.stdout

        candidate = root / "candidate.md"
        candidate.write_text(
            good.read_text(encoding="utf-8").replace(
                "# References", "The bounded contribution is bounded and bounded.\n\n# References"
            ), encoding="utf-8",
        )
        candidate_receipt = root / "candidate-receipt.json"
        write_receipt(candidate_receipt, candidate, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows")
        candidate_report = root / "candidate-report.json"
        first_candidate = run(candidate, candidate_receipt, candidate_report)
        assert first_candidate.returncode == 2
        candidate_payload = json.loads(candidate_report.read_text(encoding="utf-8"))
        semantic_candidates = [row for row in candidate_payload["findings"]
                               if row["severity"] == "candidate"]
        assert semantic_candidates
        receipt_payload = json.loads(candidate_receipt.read_text(encoding="utf-8"))
        receipt_payload["adjudications"] = [{
            "code": row["code"], "locator": row["locator"],
            "disposition": "accepted_synthesis",
            "rationale": "Independent Evaluator accepts this explicit synthesis for the fixture.",
        } for row in semantic_candidates]
        candidate_receipt.write_text(json.dumps(receipt_payload, indent=2) + "\n", encoding="utf-8")
        adjudicated = run(candidate, candidate_receipt, root / "candidate-adjudicated.json")
        assert adjudicated.returncode == 0, adjudicated.stdout + adjudicated.stderr

        bad = root / "bad.md"
        bad.write_text(
            "# Abstract\n\nRequirements engineering is often reached for after failure. "
            "These are not rungs of a ladder.\n\n# Body\n\nThe design-time bounded contribution "
            "is bounded, bounded, and bounded.\n", encoding="utf-8")
        bad_receipt = root / "bad-receipt.json"
        write_receipt(bad_receipt, bad, source_a, extract_a, source_b, extract_b,
                      quote="the whys behind the whats and hows")
        result = run(bad, bad_receipt, root / "bad-report.json")
        assert result.returncode == 2
        codes = {row["code"] for row in json.loads((root / "bad-report.json").read_text(encoding="utf-8"))["findings"]}
        assert {"TERM-COINAGE", "REGISTER-ABSENT", "INSIDER-NEGATION",
                "EMPIRICAL-UNSUPPORTED"} <= codes, codes
        suite_out = root / "suite-findings.json"
        suite = subprocess.run(
            [sys.executable, str(RUN_ALL), str(bad), "--out", str(suite_out),
             "--semantic-receipt", str(bad_receipt), "--skip-accessibility",
             "--skip-d-style-profile"], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        assert suite.returncode == 2, suite.stdout + suite.stderr
        suite_payload = json.loads(suite_out.read_text(encoding="utf-8"))
        suite_codes = {row["check_id"] for row in suite_payload["findings"]}
        assert {"TERM-COINAGE", "REGISTER-ABSENT", "INSIDER-NEGATION",
                "EMPIRICAL-UNSUPPORTED"} <= suite_codes

    print("product_assurance_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
