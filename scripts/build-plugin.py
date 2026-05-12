#!/usr/bin/env python3
"""Build the co-author-harness `.plugin` bundle for Cowork's file-upload install path.

A `.plugin` file is a ZIP archive with `.claude-plugin/plugin.json` at the
archive root and the plugin's directory tree underneath. Cowork's plugin
loader UI accepts file uploads with this extension; the bundle sidesteps the
URL/marketplace install path (which requires the repo to be public + ship a
marketplace.json).

**Bundle definition.** `git ls-tree -r HEAD --name-only` on the harness root.
Tracked files at the current HEAD go in; untracked session-scope content
(`.claude/handoffs/`, `artifacts/efficiency/<timestamp>/`, runtime outputs)
is excluded by definition. The `.gitignore` excludes `*.plugin` files, so
the previously-built bundle (if present in `.claude-plugin/`) is invisible
to `git ls-tree` and won't recurse into the new bundle.

**Defense-in-depth.** The script filters archive files from the bundle
even if `git ls-tree` returned them — protects against future `.gitignore`
drift. A nested archive file inside a `.plugin` archive violates the
Cowork loader contract.

**Output.** `<harness>/.claude-plugin/<plugin-name>.plugin` (plugin name read
from `.claude-plugin/plugin.json`).

**Usage.**

    python scripts/build-plugin.py

Or with PYTHONUTF8=1 on Windows hosts where stdlib defaults to cp949 and the
plugin tree carries §, →, em dashes, etc.:

    set PYTHONUTF8=1
    "C:\\Users\\<user>\\AppData\\Local\\Programs\\Python\\Launcher\\py.exe" \\
        scripts\\build-plugin.py

**Exit codes.**

    0  bundle written successfully
    1  required files missing from the tracked set
    2  git ls-tree failed (not a git repo? HEAD missing?)
    3  plugin.json missing or unparseable
"""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from resolve_includes import resolve_includes_in_text

# Resolve harness root from this script's location: scripts/build-plugin.py
HARNESS = Path(__file__).resolve().parent.parent

# Resolve git executable. On Windows hosts the launcher path is required
# because PATH may not include git in some shell environments.
GIT_CANDIDATES = [
    r"C:\Program Files\Git\cmd\git.exe",
    "git",  # POSIX / PATH-resolvable
]


def find_git() -> str:
    for candidate in GIT_CANDIDATES:
        if Path(candidate).is_file() or candidate == "git":
            return candidate
    return "git"


GIT = find_git()

# Sanity-check files: every bundle must include these or it's not a usable plugin
REQUIRED_FILES = (
    ".claude-plugin/plugin.json",
    "agents/planner.md",
    "skills/plugin-commands/SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "CLAUDE.md",
)


def main() -> int:
    # Read plugin.json to derive the bundle name
    manifest_path = HARNESS / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        print(f"[ERROR] missing manifest: {manifest_path}", file=sys.stderr)
        return 3
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] cannot parse {manifest_path}: {exc}", file=sys.stderr)
        return 3
    plugin_name = manifest.get("name", "plugin")
    plugin_version = manifest.get("version", "0.0.0")
    output = HARNESS / ".claude-plugin" / f"{plugin_name}.plugin"

    print(f"Harness root:  {HARNESS}")
    print(f"Plugin name:   {plugin_name}")
    print(f"Plugin ver:    {plugin_version} (manifest may be RC-deferred behind tag state)")
    print(f"Output:        {output}")

    # Get the tracked-file list at HEAD
    try:
        result = subprocess.run(
            [GIT, "-C", str(HARNESS), "ls-tree", "-r", "HEAD", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] git ls-tree failed: {exc.stderr or exc}", file=sys.stderr)
        return 2

    files = [line for line in result.stdout.splitlines() if line.strip()]
    print(f"Tracked files: {len(files)}")

    # Defense-in-depth: filter archive files even if git ls-tree returned them.
    # Nested archives violate the Cowork loader contract and can make upload
    # installs fail. The .gitignore should already exclude generated archives,
    # so this filter is belt-and-braces against future drift.
    archive_suffixes = (".plugin", ".zip")
    filtered = [f for f in files if not f.endswith(archive_suffixes)]
    excluded_archive_files = sorted(set(files) - set(filtered))
    if excluded_archive_files:
        print(f"[WARN] excluding {len(excluded_archive_files)} archive file(s) "
              f"from bundle (defense-in-depth):", file=sys.stderr)
        for f in excluded_archive_files:
            print(f"    {f}", file=sys.stderr)
    files = filtered

    # Verify required files are in the tracked set
    missing = [r for r in REQUIRED_FILES if r not in files]
    if missing:
        print(f"[ERROR] required files missing from tracked set: {missing}",
              file=sys.stderr)
        return 1
    print("All required files present.")

    # Build the .plugin (ZIP) file
    output.parent.mkdir(parents=True, exist_ok=True)
    total_size = 0
    skipped = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            src = HARNESS / rel
            if not src.is_file():
                # Submodule entry, broken symlink, or stale ls-tree row
                skipped += 1
                continue
            # Use forward slashes in archive (zip convention)
            arcname = rel.replace("\\", "/")
            if src.suffix.lower() == ".md":
                source_text = src.read_text(encoding="utf-8")
                if "<!-- include:" in source_text:
                    rendered = resolve_includes_in_text(source_text, src, HARNESS)
                    z.writestr(arcname, rendered)
                    total_size += len(rendered.encode("utf-8"))
                    continue
            z.write(src, arcname=arcname)
            total_size += src.stat().st_size

    bundle_size = output.stat().st_size
    print(f"\nBundle written: {output}")
    print(f"Source bytes:   {total_size:>12,}")
    print(f"Compressed:     {bundle_size:>12,}")
    if total_size > 0:
        print(f"Compression:    {bundle_size / total_size:.1%}")
    if skipped:
        print(f"Skipped (not a regular file): {skipped}")

    # Verify by reading back
    with zipfile.ZipFile(output) as z:
        names = z.namelist()
        print(f"Members in bundle: {len(names)}")
        for required in REQUIRED_FILES:
            if required in names:
                info = z.getinfo(required)
                print(f"  OK  {required}  ({info.file_size} bytes)")
            else:
                print(f"  [ERROR] missing from bundle: {required}", file=sys.stderr)
                return 1
        # Safety net: assert no nested archive survived.
        nested = [n for n in names if n.endswith(archive_suffixes)]
        if nested:
            print(f"[ERROR] nested archive file(s) in bundle: {nested}",
                  file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
