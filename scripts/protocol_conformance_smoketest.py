#!/usr/bin/env python3
"""Focused synthetic M1-to-FINAL protocol-conformance qualification."""

from __future__ import annotations

import json
from pathlib import Path
from assignment_fixture_support import package_scratch
import tempfile

from protocol_conformance_fixture_support import build_protocol_conformance


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="protocol-conformance-", dir=package_scratch(ROOT)
    ) as raw:
        fixture = build_protocol_conformance(Path(raw))
        report = json.loads(fixture.report.read_text(encoding="utf-8"))
        assert report["report_type"] == "protocol_conformance"
        assert report["status"] == "passed"
        assert report["claims"] == {
            "human_quality_semantic_judgment": False,
            "host_attested_separate_agents": False,
        }
        assert report["milestones"] == ["M1", "M2", "M3", "M4", "M5"]
        assert report["terminal"]["status"] == "PASS"
        assert report["candidate_adjudication"]["status"] == "passed"
        assert report["candidate_adjudication"]["fingerprint_bound"] is True
        assert report["passage_evidence"] == {
            "real_pdf_extraction": True,
            "direct_quotation": True,
            "conditioning_passage": True,
        }
        assert report["production_counts"] == {
            "consumed_assignment_receipts": 5,
            "dispatch_claims": 10,
            "dispatch_consumptions": 10,
            "verifier_transactions": 10,
            "mutation_rows": 11,
        }
        assert report["tamper_results"] == {
            "candidate_text": "ADJUDICATION-STALE",
            "dispatch_consumption": "LIFECYCLE-EVIDENCE-CLAIM",
            "extract_bytes": "EXTRACT-BINDING-STALE",
            "mutation_row": "APG-MUTATION-LEDGER-INVALID",
            "terminal_signoff": "FRC-TERMINAL-EVIDENCE-BINDING",
        }

    print("protocol_conformance_smoketest: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
