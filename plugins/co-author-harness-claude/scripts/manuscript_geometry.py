"""Shared Markdown/TeX heading geometry with offset-preserving TeX comment removal."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

def strip_tex_comments(text: str) -> str:
    """Replace unescaped TeX comments with spaces while preserving offsets/newlines."""
    out=[]
    for line in text.splitlines(keepends=True):
        match=re.search(r"(?<!\\)%",line)
        if match:
            end=len(line)-1 if line.endswith("\n") else len(line)
            line=line[:match.start()]+(" "*(end-match.start()))+("\n" if line.endswith("\n") else "")
        out.append(line)
    return "".join(out)

def heading_sections(text: str, path: Path) -> tuple[str,list[dict[str,Any]]]:
    clean=strip_tex_comments(text) if path.suffix.lower() in {".tex",".ltx"} else text
    pattern=re.compile(r"(?m)^(#{1,6})\s+(.+)$") if path.suffix.lower() not in {".tex",".ltx"} else re.compile(r"(?m)^\\(chapter|section|subsection|subsubsection)\*?\{([^}]+)\}")
    matches=list(pattern.finditer(clean)); sections=[]
    for index,match in enumerate(matches):
        sections.append({"title":match.group(2).strip(),"heading_start":match.start(),"heading_end":match.end(),"body_start":match.end(),"body_end":matches[index+1].start() if index+1<len(matches) else len(clean)})
    return clean,sections
