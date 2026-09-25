#!/usr/bin/env python3
"""destination_capability_smoketest - producer writes stay in exact governed lanes.

Hermetic: a FAKE governed root under a temp dir is added via
COAUTHOR_EXTRA_GOVERNED_ROOTS (additive-only test hook), so red-phase runs that
reach the filesystem mutate the fake tree, never `B:\\Agents\\research`. The one
real-workspace case is read-only classification.

Run:  python scripts/destination_capability_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))

import destination_capability as dc  # noqa: E402
import evidence_publication  # noqa: E402
from audit.schema import FindingsReport  # noqa: E402

PATH_HYGIENE_SPEC = importlib.util.spec_from_file_location(
    "path_hygiene_check", HARNESS / "scripts" / "path-hygiene-check.py"
)
assert PATH_HYGIENE_SPEC and PATH_HYGIENE_SPEC.loader
path_hygiene = importlib.util.module_from_spec(PATH_HYGIENE_SPEC)
PATH_HYGIENE_SPEC.loader.exec_module(path_hygiene)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(name)


def make_fake_root(base: Path) -> Path:
    fake = base / "fake-ws"
    (fake / "research" / "60_Workbench").mkdir(parents=True)
    (fake / "outputs" / "co-author-harness" / "staging").mkdir(parents=True)
    (fake / "knowledge").mkdir(parents=True)
    manifest = fake / "governance" / "output-routing" / "output_routing.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("schema_version: 1\nroutes: []\n", encoding="utf-8")
    return fake


def case_classifier() -> None:
    with tempfile.TemporaryDirectory(prefix="destcap-") as td:
        fake = make_fake_root(Path(td))
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            probe = fake / "research" / "60_Workbench" / "probe.md"
            check("canonical research path -> protected",
                  dc.classify(probe) == "protected", dc.classify(probe))
            mixed = str(probe).replace("research", "RESEARCH")
            check("case-folded alias -> protected",
                  dc.classify(mixed) == "protected", dc.classify(mixed))
            fwd = str(probe).replace("\\", "/")
            check("forward-slash alias -> protected",
                  dc.classify(fwd) == "protected", dc.classify(fwd))
            dotdot = fake / "outputs" / ".." / "research" / "60_Workbench" / "probe.md"
            check("dot-dot traversal -> protected",
                  dc.classify(dotdot) == "protected", dc.classify(dotdot))
            wiki = fake / "knowledge" / "LLM wiki" / "wiki" / "sources" / "x.md"
            check("wiki path under governed root -> protected",
                  dc.classify(wiki) == "protected", dc.classify(wiki))
            lane = fake / "outputs" / "co-author-harness" / "staging" / "w1" / "r1" / "work" / "d.md"
            check("staging lane -> staging (writable)",
                  dc.classify(lane) == "staging", dc.classify(lane))
            shipment = (fake / "research" / "60_Workbench" / "w1" /
                        "reviews" / ".harness" / "shipments" / "s1" /
                        "findings.json")
            check("research shipment lane -> shipment (writable)",
                  dc.classify(shipment) == "shipment", dc.classify(shipment))
            visible_base = fake / "research" / "60_Workbench" / "w1" / "reviews" / "harness"
            for label, path, expected in (
                ("visible shipment", visible_base / "shipments" / "s1" / "draft.md", "shipment"),
                ("visible root", visible_base, "protected"),
                ("visible shipment parent", visible_base / "shipments", "protected"),
                ("visible adjacent control", visible_base / "phase_state.json", "protected"),
                ("visible traversal", visible_base / "shipments" / "s1" / ".." / ".." / "phase_state.json", "protected"),
            ):
                check(label, dc.classify(path) == expected, dc.classify(path))
            assignment_ready = (fake / "research" / "60_Workbench" / "w1" /
                                "reviews" / ".harness" / "assignment" / "ready" /
                                "gate.json")
            check("assignment ready lane -> instrument (writable)",
                  dc.classify(assignment_ready) == "instrument",
                  dc.classify(assignment_ready))
            control_lock = (fake / "research" / "60_Workbench" / "w1" /
                            "reviews" / ".harness" / "control-plane" /
                            "authority.lock")
            check("control-plane lock -> instrument (writable)",
                  dc.classify(control_lock) == "instrument",
                  dc.classify(control_lock))
            harness_root = (fake / "research" / "60_Workbench" / "w1" /
                            "reviews" / ".harness")
            check(".harness directory without child stays protected",
                  dc.classify(harness_root) == "protected",
                  dc.classify(harness_root))
            other_work = (fake / "research" / "60_Workbench" / "w2" /
                          "reviews" / ".harness" / "assignment" / "ready" /
                          "gate.json")
            check("second work-id has its own instrument lane",
                  dc.classify(other_work) == "instrument",
                  dc.classify(other_work))
            memo = (fake / "research" / "60_Workbench" / "w1" /
                    "milestones" / "M1_project_memo.md")
            check("manuscript under live work-id stays protected",
                  dc.classify(memo) == "protected", dc.classify(memo))
            work_id = fake / "research" / "60_Workbench" / "w1"
            repin_pending = work_id / "reviews" / "repin_rebind_request.json"
            repin_applied = work_id / "reviews" / "repin_rebind_request.8.applied.json"
            repin_stale = work_id / "reviews" / "repin_rebind_request.8.abc123.stale.json"
            repin_sidecar = (work_id / "reviews" / ".harness" / "policies" /
                             "reader_accessibility.resolved.json")
            for label, path in (
                ("pending", repin_pending), ("applied", repin_applied),
                ("stale", repin_stale), ("resolved sidecar", repin_sidecar),
            ):
                check(f"exact re-pin {label} path -> repin (writable)",
                      dc.classify(path) == "repin", dc.classify(path))
            adjacent_review = work_id / "reviews" / "phase_state.json"
            check("adjacent review path remains protected",
                  dc.classify(adjacent_review) == "protected",
                  dc.classify(adjacent_review))
            check("re-pin work-id root gets container capability only through guard",
                  dc.classify(work_id) == "protected"
                  and dc.guard_repin_project_root(work_id) == "repin_container")
            shipment_parent = shipment.parents[1]
            check("shipment parent without shipment id -> protected",
                  dc.classify(shipment_parent) == "protected",
                  dc.classify(shipment_parent))
            other_out = fake / "outputs" / "adhoc" / "x.txt"
            check("outputs outside the lane -> protected",
                  dc.classify(other_out) == "protected", dc.classify(other_out))
            check("harness package path -> package",
                  dc.classify(HARNESS / "research_notes" / "x.md") == "package")
            local_staging = (HARNESS / "outputs" / "co-author-harness" /
                             "staging" / "w1" / "r1" / "work" / "d.md")
            check("package-local staging lookalike -> misrouted",
                  dc.classify(local_staging) == "misrouted",
                  dc.classify(local_staging))
            refused = None
            try:
                dc.assert_writable(local_staging)
            except dc.DestinationRefused as exc:
                refused = exc
            check("package-local staging raises DEST-MISROUTED",
                  refused is not None and refused.code == dc.DEST_MISROUTED)
            ext = Path(td) / "unrelated" / "x.txt"
            check("path outside every governed root -> external",
                  dc.classify(ext) == "external", dc.classify(ext))
            # directory alias: a link OUTSIDE the governed root that resolves INTO it
            # (an NTFS junction on Windows, a symlink elsewhere)
            link = Path(td) / "jx"
            alias_target = fake / "research" / "60_Workbench"
            if os.name == "nt":
                r = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(alias_target)],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                alias_error = "" if r.returncode == 0 else r.stderr.strip()
            else:
                try:
                    os.symlink(alias_target, link, target_is_directory=True)
                    alias_error = ""
                except OSError as exc:
                    alias_error = str(exc)
            if not alias_error:
                got = dc.classify(link / "probe.md")
                check("directory alias into research -> protected",
                      got == "protected", got)
            else:
                print("  SKIP  directory alias creation unavailable in this environment "
                      f"({alias_error[:60]})")
            refused = None
            try:
                dc.assert_writable(probe)
            except dc.DestinationRefused as exc:
                refused = exc
            check("assert_writable raises DEST-PROTECTED",
                  refused is not None and refused.code == dc.DEST_PROTECTED)
            check("assert_writable permits exact shipment child",
                  dc.assert_writable(shipment) == "shipment")
            check("assert_writable permits assignment ready child",
                  dc.assert_writable(assignment_ready) == "instrument")
            check("live work-id root stays protected",
                  dc.classify(work_id) == "protected", dc.classify(work_id))
            check("guard_instrument_lane unlocks assignment without unlocking work-id",
                  dc.guard_instrument_lane(work_id) == "instrument")
            check("guard_lifecycle_project_root unlocks only the canonical lifecycle container",
                  dc.guard_lifecycle_project_root(work_id) == "lifecycle_container")
            refused_state = None
            try:
                dc.assert_writable(work_id / "reviews" / "phase_state.json")
            except dc.DestinationRefused as exc:
                refused_state = exc
            check("phase_state remains protected outside the lifecycle transaction",
                  refused_state is not None and refused_state.code == dc.DEST_PROTECTED)
            refused_memo = None
            try:
                dc.assert_writable(memo)
            except dc.DestinationRefused as exc:
                refused_memo = exc
            check("manuscript assert_writable stays DEST-PROTECTED",
                  refused_memo is not None and refused_memo.code == dc.DEST_PROTECTED)
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def case_package_local_staging_hygiene() -> None:
    with tempfile.TemporaryDirectory(prefix="destcap-hygiene-") as td:
        root = Path(td)
        check("absent package-local staging passes hygiene",
              path_hygiene.check_repo_local_project_staging(root) == [])
        forbidden = root / "outputs" / "co-author-harness" / "staging" / "w1" / "r1"
        forbidden.mkdir(parents=True)
        findings = path_hygiene.check_repo_local_project_staging(root)
        check("present package-local staging blocks hygiene",
              len(findings) == 1 and "governed workspace root" in findings[0],
              str(findings))


def case_real_workspace_discovery() -> None:
    """Read-only: the REAL research root must classify protected via discovery."""
    ws = dc.discovered_workspace_root()
    if ws is None:
        print("  SKIP  no workspace routing manifest above this checkout "
              "(distributed install); ungoverned fail-closed covered below")
        return
    got = dc.classify(ws / "research" / "60_Workbench" / "__never_created__")
    check("real research root -> protected via discovered governance",
          got == "protected", got)
    check("real staging lane -> staging via discovered governance",
          dc.classify(ws / "outputs" / "co-author-harness" / "staging" / "w" / "r")
              == "staging")


def case_distributed_destination_discovery() -> None:
    """An installed cache discovers governance from the destination, not cwd."""
    with tempfile.TemporaryDirectory(prefix="destcap-distributed-") as td:
        base = Path(td)
        fake = make_fake_root(base)
        real = dc.discovered_workspace_root
        dc.discovered_workspace_root = lambda: None
        os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
        try:
            project = fake / "research" / "60_Workbench" / "w1"
            staging = (fake / "outputs" / "co-author-harness" / "staging" /
                       "w1" / "r1" / "draft.md")
            shipment = (project / "reviews" / ".harness" / "shipments" /
                        "s1" / "findings.json")
            check("distributed: project discovers destination governance",
                  dc.classify(project) == "protected", dc.classify(project))
            check("distributed: staging remains writable",
                  dc.classify(staging) == "staging", dc.classify(staging))
            check("distributed: shipment remains writable",
                  dc.classify(shipment) == "shipment", dc.classify(shipment))
            check("distributed: re-pin guard resolves destination governance",
                  dc.guard_repin_project_root(project) == "repin_container")
            unrelated = base / "outside" / "x.txt"
            check("distributed: unrelated path remains ungoverned",
                  dc.classify(unrelated) == "ungoverned",
                  dc.classify(unrelated))
        finally:
            dc.discovered_workspace_root = real


def case_ungoverned_fails_closed() -> None:
    """No governed root at all: every non-package destination is refused."""
    real = dc.discovered_workspace_root
    dc.discovered_workspace_root = lambda: None
    os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)
    try:
        check("ungoverned: package still writable",
              dc.classify(HARNESS / "reviews" / "x.json") == "package")
        got = dc.classify(Path(tempfile.gettempdir()) / "x.txt")
        check("ungoverned: non-package -> ungoverned", got == "ungoverned", got)
        refused = None
        try:
            dc.assert_writable(Path(tempfile.gettempdir()) / "x.txt")
        except dc.DestinationRefused as exc:
            refused = exc
        check("ungoverned: assert_writable raises DEST-UNGOVERNED",
              refused is not None and refused.code == dc.DEST_UNGOVERNED)
    finally:
        dc.discovered_workspace_root = real


# Wiring: every guarded mutator must refuse a governed project root BEFORE
# writing. Each entry: (label, argv builder given a probe root). The fake
# governed root absorbs any red-phase mutation harmlessly. Guard-first
# placement means minimal argv satisfies argparse and still exercises refusal.
def _script(name: str, *args: str):
    def build(root: Path) -> list[str]:
        return [sys.executable, str(HARNESS / "scripts" / name),
                *(a.replace("{ROOT}", str(root)) for a in args)]
    return build


WIRED_MUTATORS = [
    ("checkpoint begin",
     _script("assignment_milestone_checkpoint.py", "begin",
             "--project-root", "{ROOT}", "--milestone", "M2")),
    ("checkpoint accept",
     _script("assignment_milestone_checkpoint.py", "accept",
             "--project-root", "{ROOT}", "--milestone", "M1",
             "--checkpoint", "reviews/.harness/milestones/checkpoints/missing.json",
             "--approval-evidence", "reviews/.harness/milestones/checkpoints/missing-approval.json")),
    ("checkpoint recover",
     _script("assignment_milestone_checkpoint.py", "recover",
             "--project-root", "{ROOT}", "--acknowledgement", "x")),
    ("receipt recover",
     _script("assignment_receipt_recover.py", "--project-root", "{ROOT}")),
    ("process gate",
     _script("assignment_process_gate.py", "--project-root", "{ROOT}")),
    ("check8 prefilter",
     _script("check8_g_prefilter.py", "--project-root", "{ROOT}",
             "--manuscript", "m.md")),
    ("migrate legacy",
     _script("migrate_legacy_milestones.py", "--project-root", "{ROOT}")),
    ("migrate derived handoff",
     _script("migrate_lab_iteration_derived_handoff.py", "dry-run",
             "--project-root", "{ROOT}")),
    ("migrate milestone paths",
     _script("migrate_milestone_paths.py", "--project-root", "{ROOT}",
             "--dry-run")),
    ("migrate v0100 drop-sd-sr",
     _script("migrate_v0100_to_v0110_drop_sd_sr.py",
             "--classification", "{ROOT}\\reviews\\classification.md")),
    ("migrate v0150pre stage-profile",
     _script("migrate_v0150pre_add_stage_profile.py",
             "--path", "{ROOT}\\reviews\\phase_state.json")),
    ("migrate v090 snowball",
     _script("migrate_v090_to_v100_snowball_fields.py",
             "--project-root", "{ROOT}", "--dry-run")),
    ("native bootstrap",
     _script("native_project_bootstrap.py", "--project-root", "{ROOT}",
             "--project-name", "probe", "--title", "t",
             "--intended-reader", "r")),
    ("sk20 overlay run",
     _script("sk20_overlay_run.py", "--project-root", "{ROOT}")),
    ("sk20 preflight gate",
     _script("sk20_preflight_gate.py", "--project-root", "{ROOT}")),
    ("render lifecycle state",
     _script("render_lifecycle_state.py", "--project-root", "{ROOT}")),
    ("reader accessibility policy",
     _script("reader_accessibility_policy.py", "--project-root", "{ROOT}")),
    ("coupling health report",
     _script("coupling_health_report.py", "--project-root", "{ROOT}")),
    ("h-calibration aggregate",
     _script("aggregate_h_calibration.py", "{ROOT}")),
    ("install preflight assets",
     _script("install_preflight_assets.py", "--project-root", "{ROOT}")),
]


LIFECYCLE_MUTATORS = {"checkpoint begin", "checkpoint accept", "checkpoint recover"}


def case_mutator_wiring() -> None:
    with tempfile.TemporaryDirectory(prefix="destcap-wire-") as td:
        fake = make_fake_root(Path(td))
        probe = fake / "research" / "60_Workbench" / "wire-probe"
        env = {**os.environ, "COAUTHOR_EXTRA_GOVERNED_ROOTS": str(fake)}
        for label, build in WIRED_MUTATORS:
            probe.mkdir(parents=True, exist_ok=True)
            before = {p.relative_to(probe) for p in probe.rglob("*")}
            r = subprocess.run(build(probe), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env)
            after = {p.relative_to(probe) for p in probe.rglob("*")}
            out = (r.stdout + r.stderr)
            check(f"{label}: refuses governed root (nonzero exit)",
                  r.returncode != 0, f"rc={r.returncode}")
            dest_ok = (
                label in LIFECYCLE_MUTATORS
                and (
                    "AMC-PHASE-STATE" in out
                    or "AMC-RECOVERY-ACK" in out
                    or "AMC-RECOVERY" in out
                )
            ) or "DEST-PROTECTED" in out or (
                label == "process gate"
                and (
                    "APG-CONTRACT-MISSING" in out
                    or "--stage is required" in out
                )
            )
            check(
                f"{label}: reaches lifecycle validation"
                if label in LIFECYCLE_MUTATORS
                else f"{label}: names DEST-PROTECTED"
                if label != "process gate"
                else f"{label}: DEST-PROTECTED or read-only contract miss",
                dest_ok,
                out.strip().splitlines()[-1][:80] if out.strip() else "silent",
            )
            created = {str(x) for x in (after - before)}
            if label in LIFECYCLE_MUTATORS:
                allowed = {
                    "reviews",
                    "reviews\\.harness",
                    "reviews\\.harness\\control-plane",
                    "reviews\\.harness\\control-plane\\authority.lock",
                    "reviews\\.harness\\milestones",
                    "reviews\\.harness\\milestones\\claims",
                    "reviews\\.harness\\milestones\\checkpoints",
                    "reviews\\.harness\\milestones\\journal",
                }
                check(f"{label}: writes only lifecycle control dirs",
                      created <= allowed, f"created {sorted(created)[:3]}")
            else:
                check(f"{label}: wrote nothing", after == before,
                      f"created {sorted(created)[:3]}")


def case_output_redirect_refusals() -> None:
    """Writers with redirectable output paths must refuse a protected
    destination even when their project root / target is external, including
    alias spellings (mixed case, forward slashes)."""
    with tempfile.TemporaryDirectory(prefix="destcap-out-") as td:
        fake = make_fake_root(Path(td))
        (fake / "research" / "60_Workbench" / "probe").mkdir(parents=True, exist_ok=True)
        external = Path(td) / "external-project"
        (external / "reviews").mkdir(parents=True)
        target_md = external / "manuscript.md"
        target_md.write_text("# external target\n", encoding="utf-8")
        env = {**os.environ, "COAUTHOR_EXTRA_GOVERNED_ROOTS": str(fake)}
        protected_dir = fake / "research" / "60_Workbench" / "probe"
        alias_out = str(protected_dir / "coupling_health.md").replace(
            "research", "RESEARCH").replace("\\", "/")
        probes = [
            ("coupling-health alias output",
             [sys.executable, str(HARNESS / "scripts" / "coupling_health_report.py"),
              "--project-root", str(external), "--output-md", alias_out,
              "--output-json", str(external / "reviews" / "ok.json")]),
            ("tuner redirected output",
             [sys.executable, str(HARNESS / "scripts" / "gate_threshold_tuner.py"),
              "--project-root", str(external),
              "--output", str(protected_dir / "tuner_report.md")]),
            ("audit run_all redirected out",
             [sys.executable, str(HARNESS / "scripts" / "audit" / "run_all.py"),
              str(target_md), "--out", str(protected_dir / "findings.json")]),
            ("coupling-readiness redirected output",
             [sys.executable, str(HARNESS / "scripts" / "coupling_readiness_check.py"),
              "--project-root", str(external),
              "--output-json", str(protected_dir / "readiness.json")]),
            ("d-style profile protected project",
             [sys.executable, str(HARNESS / "scripts" / "d_style_profile_check.py"),
              "--project-root", str(protected_dir)]),
        ]
        for label, argv in probes:
            before = {p.relative_to(protected_dir) for p in protected_dir.rglob("*")}
            r = subprocess.run(argv, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env)
            after = {p.relative_to(protected_dir) for p in protected_dir.rglob("*")}
            out = r.stdout + r.stderr
            # Exactly the documented refusal code: a refusal that exits via an
            # unrelated crash (e.g. a NameError in the refusal path) passed the
            # old any-nonzero form while printing DEST-PROTECTED only inside
            # the traceback -- measured 2026-07-22 on d_style_profile_check.
            check(f"{label}: refuses with the documented code 4", r.returncode == 4,
                  f"rc={r.returncode}")
            check(f"{label}: names DEST-PROTECTED", "DEST-PROTECTED" in out,
                  out.strip().splitlines()[-1][:80] if out.strip() else "silent")
            check(f"{label}: clean diagnostic, no traceback",
                  "Traceback" not in out,
                  out.strip().splitlines()[-1][:80] if "Traceback" in out else "")
            check(f"{label}: wrote nothing into the protected root",
                  after == before,
                  f"created {sorted(str(x) for x in (after - before))[:3]}")


def case_r0_writer_refusals() -> None:
    """The three R-0 production writers refuse governed research paths."""
    with tempfile.TemporaryDirectory(prefix="destcap-r0-") as td:
        fake = make_fake_root(Path(td))
        protected = fake / "research" / "60_Workbench" / "r0-probe"
        protected.mkdir(parents=True)
        env = {**os.environ, "COAUTHOR_EXTRA_GOVERNED_ROOTS": str(fake)}
        os.environ["COAUTHOR_EXTRA_GOVERNED_ROOTS"] = str(fake)
        try:
            before = {p.relative_to(protected) for p in protected.rglob("*")}
            refused = None
            try:
                evidence_publication.publish_committed(
                    project_root=protected,
                    transaction_id="r0-probe",
                    preconditions=[],
                    inventory_preconditions=[],
                    outputs=[(protected / "out.json", b"{}\n")],
                    marker=(protected / "committed.json", b"{}\n"),
                )
            except dc.DestinationRefused as exc:
                refused = exc
            after = {p.relative_to(protected) for p in protected.rglob("*")}
            check("evidence publication raises DEST-PROTECTED",
                  refused is not None and refused.code == dc.DEST_PROTECTED)
            check("evidence publication writes nothing", after == before)

            report_path = protected / "findings.json"
            refused = None
            try:
                FindingsReport(target="r0-probe").write(report_path)
            except dc.DestinationRefused as exc:
                refused = exc
            check("audit schema writer raises DEST-PROTECTED",
                  refused is not None and refused.code == dc.DEST_PROTECTED)
            check("audit schema writer creates no report", not report_path.exists())

            # The contract-kernel CLI must read a coherent package before it
            # reaches its explicit --refresh write. Copy only its enumerated
            # inputs into the fake governed root, then prove the write refuses.
            source_kernel = HARNESS / "references" / "contract_kernel.v1.json"
            kernel_doc = json.loads(source_kernel.read_text(encoding="utf-8"))
            required = {"version.json", "README.md", "LICENSE",
                        "references/contract_kernel.v1.json"}
            required.update(row["path"] for row in kernel_doc["components"])
            for rel in sorted(required):
                source = HARNESS / rel
                destination = protected / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            kernel_path = protected / "references" / "contract_kernel.v1.json"
            kernel_before = kernel_path.read_bytes()
            result = subprocess.run(
                [sys.executable, str(HARNESS / "scripts" / "contract-kernel-check.py"),
                 "--plugin-root", str(protected), "--refresh"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=env,
            )
            output = result.stdout + result.stderr
            check("contract-kernel refresh refuses governed root",
                  result.returncode != 0 and "DEST-PROTECTED" in output,
                  output.strip().splitlines()[-1][:120] if output.strip() else "silent")
            check("contract-kernel refresh preserves kernel bytes",
                  kernel_path.read_bytes() == kernel_before)
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


def case_audit_shipment_output() -> None:
    """A read-only audit may consume a protected project while writing its
    report only to that project's exact private shipment lane."""
    with tempfile.TemporaryDirectory(prefix="destcap-shipment-audit-") as td:
        fake = make_fake_root(Path(td))
        project = fake / "research" / "60_Workbench" / "w1"
        target = project / "milestones" / "M3.md"
        target.parent.mkdir(parents=True)
        target.write_text("# M3\n\nA bounded test paragraph.\n", encoding="utf-8")
        shipment = (project / "reviews" / ".harness" / "shipments" /
                    "s1")
        output = shipment / "findings.json"
        env = {**os.environ, "COAUTHOR_EXTRA_GOVERNED_ROOTS": str(fake)}
        r = subprocess.run(
            [sys.executable, str(HARNESS / "scripts" / "audit" / "run_all.py"),
             str(target), "--project-root", str(project), "--out", str(output),
             "--skip-d-style-profile", "--skip-accessibility"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env)
        detail = (r.stdout + r.stderr).strip()[-120:]
        detail = detail.encode("ascii", "backslashreplace").decode("ascii")
        check("audit writes exact shipment output", r.returncode == 0,
              f"rc={r.returncode}: {detail}")
        check("audit shipment report exists", output.is_file())
        outside = project / "reviews" / "findings.json"
        check("audit creates no loose project report", not outside.exists())


SCRIPTS = HARNESS / "scripts"


def case_installer_workspace_and_read_only_modes() -> None:
    """Read-only modes need no write capability; installers can make a workspace.

    Regression for the 2026-09-25 audit: `check8_g_prefilter --stdout-only`
    ("do not write"), `render_lifecycle_state --check` and a `run_all --stdout`
    run with both project reports skipped were refused by the write guard, and
    an installer had no supported way to create the routing manifest.
    """
    with tempfile.TemporaryDirectory(prefix="destcap-installer-") as td:
        base = Path(td)
        fake = make_fake_root(base / "governed")
        project = fake / "research" / "60_Workbench" / "read-only-probe"
        (project / "reviews").mkdir(parents=True)
        manuscript = project / "draft.md"
        manuscript.write_text("# Draft\n\nA plain sentence for the probe.\n", encoding="utf-8")
        env = {**os.environ, "COAUTHOR_EXTRA_GOVERNED_ROOTS": str(fake)}
        check("read-only probe project is protected on every host",
              subprocess.run(
                  [sys.executable, "-c",
                   "import sys; sys.path.insert(0, sys.argv[1]);"
                   "import destination_capability as d; print(d.classify(sys.argv[2]))",
                   str(SCRIPTS), str(project)],
                  capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
              ).stdout.strip() == "protected")
        read_only = (
            ("check8_g --stdout-only",
             [sys.executable, str(SCRIPTS / "check8_g_prefilter.py"), "--project-root",
              str(project), "--manuscript", str(manuscript), "--stdout-only"], {0}),
            ("render_lifecycle_state --check",
             [sys.executable, str(SCRIPTS / "render_lifecycle_state.py"), "--project-root",
              str(project), "--check"], None),
            ("run_all --stdout with project reports skipped",
             [sys.executable, str(SCRIPTS / "audit" / "run_all.py"), str(manuscript),
              "--project-root", str(project), "--stdout", "--skip-d-style-profile",
              "--skip-accessibility"], {0}),
        )
        for label, argv, codes in read_only:
            before = sorted(p.relative_to(project) for p in project.rglob("*"))
            r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env)
            after = sorted(p.relative_to(project) for p in project.rglob("*"))
            out = r.stdout + r.stderr
            check(f"{label}: needs no write capability",
                  "DEST-" not in out and (codes is None or r.returncode in codes),
                  f"rc={r.returncode} {out.strip().splitlines()[-1][:90] if out.strip() else ''}")
            check(f"{label}: wrote nothing", before == after)

        # The same run on a host with no governed workspace at all (an installer).
        loose = base / "loose-project"
        (loose / "reviews").mkdir(parents=True)
        loose_manuscript = loose / "draft.md"
        loose_manuscript.write_text("# Draft\n\nA plain sentence.\n", encoding="utf-8")
        ungoverned_run = (
            "import runpy, sys; sys.path.insert(0, sys.argv[1]);"
            "import destination_capability as d; d.discovered_workspace_root = lambda: None;"
            "sys.argv = sys.argv[2:]; runpy.run_path(sys.argv[0], run_name='__main__')"
        )
        plain_env = {k: v for k, v in os.environ.items() if k != "COAUTHOR_EXTRA_GOVERNED_ROOTS"}
        r = subprocess.run(
            [sys.executable, "-c", ungoverned_run, str(SCRIPTS),
             str(SCRIPTS / "audit" / "run_all.py"), str(loose_manuscript),
             "--project-root", str(loose), "--stdout", "--skip-d-style-profile",
             "--skip-accessibility"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=plain_env,
        )
        check("run_all --stdout on an ungoverned host reads a project without write capability",
              r.returncode == 0 and "DEST-" not in r.stdout + r.stderr,
              f"rc={r.returncode} {(r.stdout + r.stderr).strip()[-90:]}")

        init = SCRIPTS / "init_governed_workspace.py"
        workspace = base / "installer-ws"
        r = subprocess.run([sys.executable, str(init), str(workspace)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=plain_env)
        manifest = workspace / "governance" / "output-routing" / "output_routing.yaml"
        check("initializer creates a governed workspace",
              r.returncode == 0 and manifest.is_file()
              and '"INITIALIZED"' in r.stdout, f"rc={r.returncode} {r.stderr[:90]}")
        lane = workspace / "outputs" / "co-author-harness" / "staging" / "w1" / "r1"
        check("initialized staging lane is writable",
              dc.classify(lane) == "staging", dc.classify(lane))
        check("initialized workspace root itself stays protected",
              dc.classify(workspace / "notes.md") == "protected",
              dc.classify(workspace / "notes.md"))
        first = manifest.read_bytes()
        r = subprocess.run([sys.executable, str(init), str(workspace)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=plain_env)
        check("initializer is idempotent and never overwrites the manifest",
              r.returncode == 0 and "ALREADY_INITIALIZED" in r.stdout
              and manifest.read_bytes() == first)
        nested = workspace / "nested"
        r = subprocess.run([sys.executable, str(init), str(nested)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=plain_env)
        check("initializer refuses to nest a workspace",
              r.returncode == 2 and "WORKSPACE-NESTED" in r.stderr and not nested.exists())
        inside = HARNESS / "init-governed-workspace-probe"
        r = subprocess.run([sys.executable, str(init), str(inside)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=plain_env)
        check("initializer refuses the harness package",
              r.returncode == 2 and "DEST-MISROUTED" in r.stderr and not inside.exists())


def main() -> int:
    print("destination_capability_smoketest")
    for fn in (case_classifier, case_package_local_staging_hygiene,
                case_real_workspace_discovery,
                case_distributed_destination_discovery,
                case_ungoverned_fails_closed, case_mutator_wiring,
                case_output_redirect_refusals, case_r0_writer_refusals,
                case_audit_shipment_output,
                case_installer_workspace_and_read_only_modes):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("PASS: producer boundary permits package, staging, shipment, and .harness instrument scratch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
