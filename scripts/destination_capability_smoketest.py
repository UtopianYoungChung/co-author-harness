#!/usr/bin/env python3
"""destination_capability_smoketest - the producer boundary refuses governed writes.

Hermetic: a FAKE governed root under a temp dir is added via
COAUTHOR_EXTRA_GOVERNED_ROOTS (additive-only test hook), so red-phase runs that
reach the filesystem mutate the fake tree, never `B:\\Agents\\research`. The one
real-workspace case is read-only classification.

Run:  python scripts/destination_capability_smoketest.py
Exit: 0 all pass; 1 a case failed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))

import destination_capability as dc  # noqa: E402

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
            other_out = fake / "outputs" / "adhoc" / "x.txt"
            check("outputs outside the lane -> protected",
                  dc.classify(other_out) == "protected", dc.classify(other_out))
            check("harness package path -> package",
                  dc.classify(HARNESS / "research_notes" / "x.md") == "package")
            ext = Path(td) / "unrelated" / "x.txt"
            check("path outside every governed root -> external",
                  dc.classify(ext) == "external", dc.classify(ext))
            # junction alias: a link OUTSIDE the governed root that resolves INTO it
            link = Path(td) / "jx"
            r = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link),
                 str(fake / "research" / "60_Workbench")],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                got = dc.classify(link / "probe.md")
                check("junction alias into research -> protected",
                      got == "protected", got)
            else:
                print("  SKIP  junction creation unavailable in this environment "
                      f"({r.stderr.strip()[:60]})")
            refused = None
            try:
                dc.assert_writable(probe)
            except dc.DestinationRefused as exc:
                refused = exc
            check("assert_writable raises DEST-PROTECTED",
                  refused is not None and refused.code == dc.DEST_PROTECTED)
        finally:
            os.environ.pop("COAUTHOR_EXTRA_GOVERNED_ROOTS", None)


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
]


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
            check(f"{label}: names DEST-PROTECTED", "DEST-PROTECTED" in out,
                  out.strip().splitlines()[-1][:80] if out.strip() else "silent")
            check(f"{label}: wrote nothing", after == before,
                  f"created {sorted(str(x) for x in (after - before))[:3]}")


def main() -> int:
    print("destination_capability_smoketest")
    for fn in (case_classifier, case_real_workspace_discovery,
               case_ungoverned_fails_closed, case_mutator_wiring):
        print(f"{fn.__name__}:")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__, False, f"raised {type(exc).__name__}: {exc}")
        print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} case(s): {FAILURES}")
        return 1
    print("PASS: producer boundary refuses every governed write destination")
    return 0


if __name__ == "__main__":
    sys.exit(main())
