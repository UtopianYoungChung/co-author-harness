"""Source-positioned Markdown prose inventory for centroid-check.

Offsets are half-open UTF-8 byte offsets in the original manuscript, not in
the binder's newline-normalized scope string.
"""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from typing import Any


HEADING = re.compile(r"^\s*#{1,6}\s+")
LIST = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
QUOTE = re.compile(r"^\s*>\s?")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
THEMATIC_BREAK = re.compile(r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$")
TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
REFERENCE_HEADING = re.compile(r"^(references|bibliography|works cited|notes)\s*$", re.I)
ABBREVIATIONS = frozenset({"dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "vs", "etc", "fig", "eq", "no", "vol", "pp", "p", "e.g", "i.e", "et al"})
INITIAL = re.compile(r"(?:\b[A-Z]\.)+$")


def _sentence_spans(block: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    index = 0
    while index < len(block):
        char = block[index]
        if char not in ".!?":
            index += 1
            continue
        end = index + 1
        if char == ".":
            before = block[max(0, end - 32):end]
            if re.search(r"\b(?:e\.g|i\.e|et al)\.$", before, re.I):
                index += 1
                continue
            word = re.search(r"([\w.]+)\.$", before)
            token = word.group(1) if word else ""
            if token.lower() in ABBREVIATIONS or INITIAL.search(before) or (index + 1 < len(block) and block[index + 1].isdigit()):
                index += 1
                continue
        while end < len(block) and block[end] in '\"”’\')]}' :
            end += 1
        if end < len(block) and not block[end].isspace():
            index += 1
            continue
        next_nonspace = end
        while next_nonspace < len(block) and block[next_nonspace].isspace():
            next_nonspace += 1
        if next_nonspace == len(block):
            break
        left = start
        while left < end and block[left].isspace():
            left += 1
        if left < end:
            spans.append((left, end))
        start = end
        index = end
    left = start
    while left < len(block) and block[left].isspace():
        left += 1
    right = len(block)
    while right > left and block[right - 1].isspace():
        right -= 1
    if left < right:
        spans.append((left, right))
    return spans


def inventory(text: str, scope: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return sentence, paragraph, and within-paragraph pair inventories."""
    lines = text.splitlines(keepends=True)
    byte_offsets = [0]
    newline_positions: list[int] = []
    for index, char in enumerate(text):
        byte_offsets.append(byte_offsets[-1] + len(char.encode("utf-8")))
        if char == "\n":
            newline_positions.append(index)
    first = int(scope["start_line"])
    last = int(scope["end_line"])
    sentences: list[dict[str, Any]] = []
    paragraphs: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    char_at = 0
    active: list[tuple[str, int]] = []
    fenced: tuple[str, int] | None = None
    yaml = bool(lines and lines[0].strip() == "---")
    references = False
    heading_level = 0
    pending_reference_heading: str | None = None

    def flush() -> None:
        if not active:
            return
        paragraph_id = f"p{len(paragraphs) + 1}"
        # Text is contiguous in the source, preserving line breaks and offsets.
        begin = active[0][1]
        finish = active[-1][1] + len(active[-1][0])
        block = text[begin:finish]
        ids: list[str] = []
        for local_start, local_end in _sentence_spans(block):
            start = begin + local_start
            end = begin + local_end
            excerpt = text[start:end]
            sid = f"s{len(sentences) + 1}"
            ids.append(sid)
            sentences.append({
                "id": sid, "text": excerpt,
                "sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                "start_utf8": byte_offsets[start],
                "end_utf8": byte_offsets[end],
                "start_line": bisect_right(newline_positions, start - 1) + 1,
                "end_line": bisect_right(newline_positions, max(start, end - 1) - 1) + 1,
                "paragraph_id": paragraph_id,
            })
        if ids:
            paragraphs.append({"id": paragraph_id, "sentence_ids": ids,
                               "previous_id": paragraphs[-1]["id"] if paragraphs else None,
                               "next_id": None})
            if len(paragraphs) > 1:
                paragraphs[-2]["next_id"] = paragraph_id
            for left_id, right_id in zip(ids, ids[1:]):
                pairs.append({"id": f"pair{len(pairs) + 1}", "left_id": left_id,
                              "right_id": right_id, "verdict": "not_run"})
        active.clear()

    for line_no, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        if yaml:
            flush()
            if line_no > 1 and stripped in {"---", "..."}:
                yaml = False
            char_at += len(raw)
            continue
        if fenced is not None:
            flush()
            close = FENCE_CLOSE.match(line)
            if close and close.group(1)[0] == fenced[0] and len(close.group(1)) >= fenced[1]:
                fenced = None
            char_at += len(raw)
            continue
        opening = FENCE_OPEN.match(line)
        if opening:
            flush()
            fenced = (opening.group(1)[0], len(opening.group(1)))
            char_at += len(raw)
            continue
        if line_no < first or line_no > last:
            flush()
            char_at += len(raw)
            continue
        if line.startswith("    ") or line.startswith("\t"):
            flush()
            char_at += len(raw)
            continue
        setext = SETEXT.match(line)
        if setext:
            heading_text = (text[active[0][1]:active[-1][1] + len(active[-1][0])].strip()
                            if active else pending_reference_heading)
            active.clear()
            pending_reference_heading = None
            if heading_text:
                level = 1 if setext.group(1).startswith("=") else 2
                if references and level <= heading_level:
                    references = False
                if REFERENCE_HEADING.fullmatch(heading_text):
                    references = True
                    heading_level = level
            char_at += len(raw)
            continue
        if THEMATIC_BREAK.match(line):
            flush()
            pending_reference_heading = None
            char_at += len(raw)
            continue
        if HEADING.match(line):
            flush()
            pending_reference_heading = None
            level = len(line.lstrip()) - len(line.lstrip().lstrip("#"))
            heading_text = re.sub(r"\s+#+\s*$", "", line.lstrip().lstrip("#").strip())
            if references and level <= heading_level:
                references = False
            if REFERENCE_HEADING.fullmatch(heading_text):
                references = True
                heading_level = level
            char_at += len(raw)
            continue
        if references or not stripped or TABLE_DIVIDER.match(line) or ("|" in line and line.count("|") >= 2) or re.fullmatch(r"!\[[^]]*\]\([^)]*\)", stripped):
            flush()
            pending_reference_heading = stripped if references and stripped else None
            char_at += len(raw)
            continue
        prefix = LIST.match(line) or QUOTE.match(line)
        if prefix:
            flush()
            offset = len(prefix.group(0))
            active.append((line[offset:], char_at + offset))
            flush()
        else:
            offset = len(line) - len(line.lstrip())
            active.append((line[offset:] + raw[len(line):], char_at + offset))
        char_at += len(raw)
    flush()
    return sentences, paragraphs, pairs
