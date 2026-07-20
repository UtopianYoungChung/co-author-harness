#!/usr/bin/env python3
"""
co-author-harness — loader-compat-check.py

Static loader-compatibility checks for the built .plugin archive. Runs every
check that is diagnosable from the .plugin file alone:

  1. ZIP integrity (CRC + truncation; zipfile.testzip()).
  2. File enumeration + zero-byte / oversize audit.
  3. Manifest schema check (.claude-plugin/plugin.json required fields,
     semver-shaped version, name without slashes/whitespace, 300-char
     description budget per manifest-coherence-check.py, 12-keyword budget).
  4. Marketplace self-reference parity (.claude-plugin/marketplace.json:
     plugins[] entry whose name matches plugin.json — version match,
     description match, source format != bare "." or "..").
  5. Path-encoding scan (no backslashes, no absolute paths, no .. traversal,
     no non-ASCII bytes in member paths, no path components >255 bytes,
     no reserved Windows basenames).
  6. Required-files presence (every skills/<name>/ has SKILL.md; agents/
     and commands/ are all .md; README.md and CHANGELOG.md at archive root).
  7. SKILL.md frontmatter validity (CRLF-tolerant regex; PyYAML parse;
     `name` and `description` populated; description <= 500 chars per
     release-gate.sh Phase 0.2 safety margin).
  8. No nested archives (no *.plugin or *.zip members; loader contract:
     a .plugin ZIP cannot contain another ZIP).
  9. Dry-run extract + rezip-byte-count sanity (extracted-bytes equality
     with ZipInfo sum; rezip within 5% of original).
 10. Peer-plugin description-length distribution comparison (auto-discovers
     peer root: walks up from plugin root looking for a sibling
     mnt/.remote-plugins/ — Linux Cowork-session convention — or
     local-agent-mode-sessions/*/*/rpm/ — Windows host convention).

What this check CANNOT verify: the loader's runtime path (skill discovery,
command registration, agent dispatch wiring). For that, the .plugin must be
loaded into a Claude Code or Cowork session and exercised end-to-end.

Usage:
    python scripts/loader-compat-check.py --plugin-root .
    python scripts/loader-compat-check.py --plugin-root . --plugin-file path/to/foo.plugin
    python scripts/loader-compat-check.py --plugin-root . --peer-root /path/to/.remote-plugins

Exit codes:
    0 — CLEAR or PASS WITH WARNINGS
    1 — BLOCKED (one or more BLOCK findings)
    2 — usage / environment error
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Tuple


# Release verification must work on native Windows consoles whose inherited
# ANSI code page cannot encode this check's own Unicode headings. Establish an
# explicit output contract before any diagnostic is printed.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


RESERVED_WIN_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


# ---------------------------------------------------------------------------
# Reporting infrastructure
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.findings: List[Tuple[str, str, str]] = []

    def emit(self, severity: str, check_id: str, message: str) -> None:
        self.findings.append((severity, check_id, message))
        print(f"[{severity}] {check_id}: {message}")

    def blocks(self) -> List[Tuple[str, str, str]]:
        return [f for f in self.findings if f[0] == "BLOCK"]

    def warns(self) -> List[Tuple[str, str, str]]:
        return [f for f in self.findings if f[0] == "WARN"]

    def passes(self) -> List[Tuple[str, str, str]]:
        return [f for f in self.findings if f[0] == "PASS"]

    def infos(self) -> List[Tuple[str, str, str]]:
        return [f for f in self.findings if f[0] == "INFO"]


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_plugin_file(plugin_root: Path, manifest_name: str) -> Optional[Path]:
    """Default convention: <plugin-root>/.claude-plugin/<name>.plugin."""
    candidate = plugin_root / ".claude-plugin" / f"{manifest_name}.plugin"
    if candidate.is_file():
        return candidate
    # Fallback: any *.plugin under .claude-plugin/
    matches = list((plugin_root / ".claude-plugin").glob("*.plugin"))
    if len(matches) == 1:
        return matches[0]
    return None


def discover_peer_root(plugin_root: Path) -> Optional[Path]:
    """Walk up from plugin_root looking for a sibling .remote-plugins/ (Linux
    Cowork-session convention) or a local-agent-mode-sessions/.../rpm/
    directory (Windows host convention)."""
    probe = plugin_root.resolve()
    seen = set()
    while probe not in seen and probe != probe.parent:
        seen.add(probe)
        # Linux Cowork-session layout: <session>/mnt/.remote-plugins/
        candidate = probe / "mnt" / ".remote-plugins"
        if candidate.is_dir():
            return candidate
        probe = probe.parent
    # Windows host layout: %APPDATA%\Claude\local-agent-mode-sessions\<>\<>\rpm\
    # This is host-specific; we return None if not found.
    return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_zip_integrity(report: Report, plugin_path: Path) -> bool:
    section("CHECK 1 — ZIP integrity (CRC + truncation)")
    if not plugin_path.exists():
        report.emit("BLOCK", "C1.exists", f"Bundle not found at {plugin_path}")
        return False
    try:
        with zipfile.ZipFile(plugin_path) as z:
            bad = z.testzip()
        if bad is None:
            report.emit("PASS", "C1.crc", "All member CRCs valid (testzip returned None)")
        else:
            report.emit("BLOCK", "C1.crc", f"First bad member: {bad}")
            return False
    except zipfile.BadZipFile as e:
        report.emit("BLOCK", "C1.format", f"Not a valid ZIP: {e}")
        return False
    report.emit("INFO", "C1.size", f"Bundle on disk: {plugin_path.stat().st_size:,} bytes")
    return True


def check_enumeration(report: Report, plugin_path: Path) -> Tuple[List[zipfile.ZipInfo], int]:
    section("CHECK 2 — File enumeration + size audit")
    with zipfile.ZipFile(plugin_path) as z:
        members = z.infolist()

    zero_byte = [m for m in members if m.file_size == 0 and not m.is_dir()]
    oversize = [m for m in members if m.file_size > 5 * 1024 * 1024]
    total_uncompressed = sum(m.file_size for m in members)
    total_compressed = sum(m.compress_size for m in members)

    report.emit("INFO", "C2.count",
                f"{len(members)} entries; {sum(1 for m in members if m.is_dir())} dirs")
    report.emit("INFO", "C2.bytes",
                f"{total_uncompressed:,} uncompressed / {total_compressed:,} compressed bytes")

    if zero_byte:
        for m in zero_byte:
            report.emit("WARN", "C2.zero", f"Zero-byte file: {m.filename}")
    else:
        report.emit("PASS", "C2.zero", "No zero-byte files")

    if oversize:
        for m in oversize:
            report.emit("WARN", "C2.large",
                        f"Member > 5 MB: {m.filename} ({m.file_size:,} bytes)")
    else:
        report.emit("PASS", "C2.large", "No members exceed 5 MB")

    return members, total_uncompressed


def check_manifest(report: Report, plugin_path: Path) -> Optional[dict]:
    section("CHECK 3 — Manifest schema (.claude-plugin/plugin.json)")
    with zipfile.ZipFile(plugin_path) as z:
        if ".claude-plugin/plugin.json" not in z.namelist():
            report.emit("BLOCK", "C3.exists",
                        "plugin.json not at .claude-plugin/plugin.json (archive root)")
            return None
        with z.open(".claude-plugin/plugin.json") as f:
            manifest_bytes = f.read()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as e:
        report.emit("BLOCK", "C3.json", f"plugin.json is not valid JSON: {e}")
        return None

    report.emit("PASS", "C3.json", "plugin.json parses as JSON")

    for field in ("name", "version", "description"):
        if field not in manifest:
            report.emit("BLOCK", "C3.field", f"Missing required field: {field}")
        elif not isinstance(manifest[field], str):
            report.emit("BLOCK", "C3.field",
                        f"Field {field!r} is not a string: {type(manifest[field]).__name__}")
        elif not manifest[field].strip():
            report.emit("BLOCK", "C3.field", f"Field {field!r} is empty")
        else:
            value = manifest[field]
            shown = value[:60] + ("..." if len(value) > 60 else "")
            report.emit("PASS", "C3.field", f"{field}={shown!r}")

    name = manifest.get("name", "")
    if re.search(r"[/\\\s]", name):
        report.emit("BLOCK", "C3.name-shape",
                    f"name {name!r} contains slash/backslash/whitespace")
    else:
        report.emit("PASS", "C3.name-shape", "name has no slashes/whitespace")

    version = manifest.get("version", "")
    if not re.match(r"^\d+\.\d+\.\d+(?:[-+].+)?$", version):
        report.emit("BLOCK", "C3.version-shape", f"version {version!r} is not semver")
    else:
        report.emit("PASS", "C3.version-shape", f"version is semver ({version!r})")

    desc_len = len(manifest.get("description", ""))
    if desc_len > 300:
        report.emit("WARN", "C3.desc-len",
                    f"Description length {desc_len} exceeds 300-char budget")
    else:
        report.emit("PASS", "C3.desc-len",
                    f"Description length {desc_len} <= 300-char budget")

    keywords = manifest.get("keywords", [])
    if not isinstance(keywords, list):
        report.emit("WARN", "C3.kw-type",
                    f"keywords is not a list: {type(keywords).__name__}")
    elif len(keywords) > 12:
        report.emit("WARN", "C3.kw-count",
                    f"keywords count {len(keywords)} exceeds 12-entry budget")
    else:
        report.emit("PASS", "C3.kw", f"keywords list of {len(keywords)} items")

    return manifest


def check_marketplace_parity(report: Report, plugin_path: Path, manifest: dict) -> None:
    section("CHECK 4 — marketplace.json self-reference parity")
    with zipfile.ZipFile(plugin_path) as z:
        if ".claude-plugin/marketplace.json" not in z.namelist():
            report.emit("INFO", "C4.exists",
                        "marketplace.json absent (optional file; not a blocker)")
            return
        with z.open(".claude-plugin/marketplace.json") as f:
            marketplace = json.loads(f.read())

    plugins_list = marketplace.get("plugins", [])
    name = manifest.get("name", "")
    self_entries = [p for p in plugins_list if p.get("name") == name]
    if not self_entries:
        report.emit("WARN", "C4.self",
                    "marketplace.json has plugins[] but no self-referencing entry")
        return
    if len(self_entries) > 1:
        report.emit("WARN", "C4.self-count",
                    f"{len(self_entries)} self-referencing entries (expected 1)")
        return

    entry = self_entries[0]
    if entry.get("version") != manifest.get("version"):
        report.emit("BLOCK", "C4.version",
                    f"marketplace self-version {entry.get('version')!r} != "
                    f"plugin.json version {manifest.get('version')!r}")
    else:
        report.emit("PASS", "C4.version",
                    f"marketplace self-version matches plugin.json "
                    f"({manifest.get('version')!r})")

    if entry.get("description") != manifest.get("description"):
        report.emit("WARN", "C4.desc",
                    "marketplace self-description differs from plugin.json description")
    else:
        report.emit("PASS", "C4.desc",
                    "marketplace self-description matches plugin.json")

    source = entry.get("source", "")
    if source in (".", ".."):
        report.emit("BLOCK", "C4.source-format",
                    f"marketplace source {source!r} is bare-dot "
                    f"(loader rejects); use {source}/ instead")
    elif not source:
        report.emit("WARN", "C4.source-empty", "marketplace self-entry has empty source")
    else:
        report.emit("PASS", "C4.source", f"marketplace source format ok ({source!r})")


def check_path_encoding(report: Report, members: List[zipfile.ZipInfo]) -> None:
    section("CHECK 5 — Path-encoding scan")
    issues = defaultdict(list)
    for m in members:
        n = m.filename
        if "\\" in n:
            issues["backslash"].append(n)
        if n.startswith("/") or (len(n) >= 2 and n[1] == ":"):
            issues["absolute"].append(n)
        if ".." in n.split("/"):
            issues["traversal"].append(n)
        try:
            n.encode("ascii")
        except UnicodeEncodeError:
            issues["non-ascii"].append(n)
        for component in n.split("/"):
            if len(component.encode("utf-8")) > 255:
                issues["component-len"].append(n)
                break
        base = n.rsplit("/", 1)[-1].rsplit(".", 1)[0].upper()
        if base in RESERVED_WIN_NAMES:
            issues["reserved"].append(n)

    for kind, examples in issues.items():
        sev = "BLOCK" if kind in ("traversal", "absolute") else "WARN"
        report.emit(sev, f"C5.{kind}",
                    f"{len(examples)} member(s) flagged; first: {examples[0]}")
    if not issues:
        report.emit("PASS", "C5", f"All {len(members)} member paths use safe encoding")


def check_required_files(report: Report, plugin_path: Path) -> None:
    section("CHECK 6 — Required-files presence")
    with zipfile.ZipFile(plugin_path) as z:
        namelist = set(z.namelist())

    skill_dirs = sorted({n.split("/", 2)[1] for n in namelist
                          if n.startswith("skills/") and "/" in n[len("skills/"):]})
    missing = [s for s in skill_dirs if f"skills/{s}/SKILL.md" not in namelist]
    if missing:
        for s in missing:
            report.emit("BLOCK", "C6.skill-md", f"skills/{s}/ has no SKILL.md")
    else:
        report.emit("PASS", "C6.skill-md", f"All {len(skill_dirs)} skill dirs have SKILL.md")

    agent_files = sorted(n for n in namelist
                          if n.startswith("agents/") and not n.endswith("/"))
    non_md_agents = [n for n in agent_files if not n.endswith(".md")]
    if non_md_agents:
        report.emit("WARN", "C6.agents",
                    f"{len(non_md_agents)} non-md files in agents/: {non_md_agents[0]}")
    else:
        report.emit("PASS", "C6.agents", f"All {len(agent_files)} agent files are .md")

    command_files = sorted(n for n in namelist
                            if n.startswith("commands/") and not n.endswith("/"))
    if command_files:
        non_md_commands = [n for n in command_files if not n.endswith(".md")]
        if non_md_commands:
            report.emit("WARN", "C6.commands",
                        f"{len(non_md_commands)} non-md files in commands/: {non_md_commands[0]}")
        else:
            report.emit("PASS", "C6.commands",
                        f"All {len(command_files)} command files are .md")

    if "README.md" in namelist:
        report.emit("PASS", "C6.readme", "README.md present at archive root")
    else:
        report.emit("WARN", "C6.readme", "README.md not at archive root")

    if "CHANGELOG.md" in namelist:
        report.emit("PASS", "C6.changelog", "CHANGELOG.md present at archive root")
    else:
        report.emit("WARN", "C6.changelog", "CHANGELOG.md not at archive root")


def check_skill_frontmatter(report: Report, plugin_path: Path) -> None:
    section("CHECK 7 — SKILL.md frontmatter validity")
    try:
        import yaml  # type: ignore
        have_yaml = True
    except ImportError:
        have_yaml = False
        report.emit("WARN", "C7.yaml",
                    "PyYAML not available; skill frontmatter checks degraded to regex-only")

    with zipfile.ZipFile(plugin_path) as z:
        skill_md_paths = sorted(n for n in z.namelist()
                                  if n.startswith("skills/") and n.endswith("/SKILL.md"))
        problems = 0
        long_descs = 0
        # CRLF-tolerant regex — files authored on Windows have CRLF line endings.
        FM_REGEX = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
        for path in skill_md_paths:
            with z.open(path) as f:
                text = f.read().decode("utf-8", errors="replace")
            m = FM_REGEX.search(text)
            if not m:
                report.emit("WARN", "C7.fm", f"{path}: no YAML frontmatter")
                problems += 1
                continue
            if have_yaml:
                try:
                    fm = yaml.safe_load(m.group(1))
                except yaml.YAMLError as e:
                    report.emit("BLOCK", "C7.fm-parse", f"{path}: YAML parse error: {e}")
                    problems += 1
                    continue
            else:
                dm = re.search(r"^description:\s*(.+)$", m.group(1), re.M)
                fm = {"description": (dm.group(1).strip() if dm else "")}
            if not fm or not isinstance(fm, dict):
                report.emit("WARN", "C7.fm-shape", f"{path}: frontmatter is not a mapping")
                problems += 1
                continue
            if not str(fm.get("name", "")).strip():
                report.emit("WARN", "C7.fm-name", f"{path}: missing or empty name")
                problems += 1
            desc = str(fm.get("description") or "")
            if not desc:
                report.emit("WARN", "C7.fm-desc", f"{path}: empty description")
                problems += 1
            if len(desc) > 500:
                report.emit("WARN", "C7.fm-desc-len",
                            f"{path}: description {len(desc)} chars exceeds "
                            f"500-char safety margin")
                long_descs += 1
        if problems == 0 and long_descs == 0:
            report.emit("PASS", "C7",
                        f"All {len(skill_md_paths)} SKILL.md files have valid frontmatter "
                        f"and descriptions <= 500 chars")


def check_no_nested(report: Report, members: List[zipfile.ZipInfo]) -> None:
    section("CHECK 8 — No nested archives")
    nested = [m.filename for m in members
                if m.filename.endswith((".plugin", ".zip"))]
    if nested:
        for n in nested:
            report.emit("BLOCK", "C8.nested",
                        f"Nested archive: {n} (loader contract: zip cannot contain nested zip)")
    else:
        report.emit("PASS", "C8", "No nested .plugin or .zip files")


def check_extract_rezip(report: Report, plugin_path: Path, total_uncompressed: int) -> None:
    section("CHECK 9 — Dry-run extract + rezip sanity")
    bundle_size = plugin_path.stat().st_size
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        try:
            with zipfile.ZipFile(plugin_path) as z:
                z.extractall(td_path)
        except Exception as e:
            report.emit("BLOCK", "C9.extract", f"Extract failed: {e}")
            return
        extracted_files = list(td_path.rglob("*"))
        extracted_total = sum(p.stat().st_size for p in extracted_files if p.is_file())
        if extracted_total != total_uncompressed:
            report.emit("WARN", "C9.bytes",
                        f"Extracted bytes {extracted_total:,} != "
                        f"ZipInfo sum {total_uncompressed:,}")
        else:
            report.emit("PASS", "C9.bytes",
                        f"Extracted bytes match ZipInfo sum ({extracted_total:,})")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
            for p in sorted(extracted_files):
                if p.is_file():
                    arcname = p.relative_to(td_path).as_posix()
                    out.write(p, arcname)
        rezipped_size = buf.tell()
        ratio = rezipped_size / bundle_size if bundle_size else 0
        if 0.95 <= ratio <= 1.05:
            report.emit("PASS", "C9.rezip",
                        f"Re-zipped size {rezipped_size:,} within 5% of original "
                        f"{bundle_size:,} (ratio {ratio:.3f})")
        else:
            report.emit("WARN", "C9.rezip",
                        f"Re-zipped size {rezipped_size:,} differs from original "
                        f"{bundle_size:,} by {abs(1-ratio)*100:.1f}%")


def check_peer_distribution(report: Report, manifest: dict, peer_root: Optional[Path]) -> None:
    section("CHECK 10 — Peer-plugin description-length distribution")
    if peer_root is None or not peer_root.exists():
        report.emit("INFO", "C10.peer-root",
                    f"No peer root reachable; skipping empirical distribution check")
        return

    name = manifest.get("name", "")
    desc_len = len(manifest.get("description", ""))
    peer_lens: List[int] = []
    for sub in peer_root.iterdir():
        if not sub.is_dir():
            continue
        peer_manifest = sub / ".claude-plugin" / "plugin.json"
        if not peer_manifest.exists():
            continue
        try:
            d = json.loads(peer_manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("name") == name:
            continue
        peer_lens.append(len(d.get("description", "")))

    if not peer_lens:
        report.emit("INFO", "C10.peers", f"No peer manifests found under {peer_root}")
        return

    peer_lens.sort()
    peer_min = peer_lens[0]
    peer_max = peer_lens[-1]
    p75_idx = max(0, math.ceil(0.75 * len(peer_lens)) - 1)
    peer_p75 = peer_lens[p75_idx]
    report.emit("INFO", "C10.peers",
                f"N={len(peer_lens)}; min={peer_min}, p75={peer_p75}, "
                f"max={peer_max}; ours={desc_len}")
    if desc_len > peer_max:
        report.emit("BLOCK", "C10.dist",
                    f"Our description length {desc_len} > peer max {peer_max}")
    elif desc_len > peer_p75:
        report.emit("WARN", "C10.dist",
                    f"Our description length {desc_len} > peer p75 {peer_p75}")
    else:
        report.emit("PASS", "C10.dist",
                    f"Our description length {desc_len} <= peer p75 {peer_p75}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Static loader-compatibility checks for the built .plugin archive."
    )
    ap.add_argument("--plugin-root", required=True, type=Path,
                     help="Plugin source root (the directory containing .claude-plugin/).")
    ap.add_argument("--plugin-file", type=Path, default=None,
                     help="Path to the .plugin archive. Defaults to "
                          "<plugin-root>/.claude-plugin/<manifest-name>.plugin.")
    ap.add_argument("--peer-root", type=Path, default=None,
                     help="Override peer-plugin root for the C10 distribution check. "
                          "If omitted, auto-discovered from plugin-root.")
    args = ap.parse_args()

    plugin_root = args.plugin_root.resolve()
    if not plugin_root.is_dir():
        print(f"ERROR: --plugin-root {plugin_root} is not a directory", file=sys.stderr)
        return 2

    src_manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not src_manifest_path.is_file():
        print(f"ERROR: source manifest missing: {src_manifest_path}", file=sys.stderr)
        return 2
    try:
        src_manifest = json.loads(src_manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: source manifest unparseable: {e}", file=sys.stderr)
        return 2
    manifest_name = src_manifest.get("name", "")

    plugin_path = args.plugin_file
    if plugin_path is None:
        plugin_path = discover_plugin_file(plugin_root, manifest_name)
        if plugin_path is None:
            print(f"ERROR: could not locate .plugin file under "
                  f"{plugin_root / '.claude-plugin'}; supply --plugin-file",
                  file=sys.stderr)
            return 2
    plugin_path = plugin_path.resolve()

    peer_root = args.peer_root
    if peer_root is None:
        peer_root = discover_peer_root(plugin_root)

    print("=" * 70)
    print("co-author-harness — loader-compat-check")
    print("=" * 70)
    print(f"Plugin root:  {plugin_root}")
    print(f"Plugin file:  {plugin_path}")
    print(f"Peer root:    {peer_root if peer_root else '<not found>'}")

    report = Report()

    if not check_zip_integrity(report, plugin_path):
        return 1
    members, total_uncompressed = check_enumeration(report, plugin_path)
    manifest = check_manifest(report, plugin_path)
    if manifest is None:
        return 1
    check_marketplace_parity(report, plugin_path, manifest)
    check_path_encoding(report, members)
    check_required_files(report, plugin_path)
    check_skill_frontmatter(report, plugin_path)
    check_no_nested(report, members)
    check_extract_rezip(report, plugin_path, total_uncompressed)
    check_peer_distribution(report, manifest, peer_root)

    section("VERDICT")
    blocks = report.blocks()
    warns = report.warns()
    passes = report.passes()
    infos = report.infos()
    print(f"PASS:  {len(passes)}")
    print(f"WARN:  {len(warns)}")
    print(f"BLOCK: {len(blocks)}")
    print(f"INFO:  {len(infos)}")
    print()

    if blocks:
        print(">>> VERDICT: BLOCKED")
        for sev, cid, msg in blocks:
            print(f"  [{sev}] {cid}: {msg}")
        return 1
    if warns:
        print(">>> VERDICT: PASS WITH WARNINGS")
        for sev, cid, msg in warns:
            print(f"  [{sev}] {cid}: {msg}")
        return 0
    print(">>> VERDICT: CLEAR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
