#!/usr/bin/env python3
"""Extract PDF annotations (comments, highlights, sticky notes) from a PDF."""
import sys
import json

PDF = r"B:\Agents\research\30_Research\AIWare\PART I\assets\AIWare2026_CameraReady_Package\aiware2026_submission_Camera-Ready_with comments.pdf"

try:
    import pypdf
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "--quiet"])
    import pypdf

reader = pypdf.PdfReader(PDF)
print(f"PDF: {PDF}")
print(f"Pages: {len(reader.pages)}")
print("=" * 80)

total = 0
for i, page in enumerate(reader.pages, start=1):
    annots = page.get("/Annots")
    if not annots:
        continue
    # resolve indirect
    if hasattr(annots, "get_object"):
        annots = annots.get_object()
    for a in annots:
        try:
            obj = a.get_object()
        except Exception:
            obj = a
        subtype = obj.get("/Subtype")
        contents = obj.get("/Contents")
        author = obj.get("/T")
        title = obj.get("/Subj") or obj.get("/NM")
        rect = obj.get("/Rect")
        # Try to get the highlighted text reference
        try:
            page_text_for_rect = ""
            if rect and subtype in ("/Highlight", "/Underline", "/StrikeOut", "/Squiggly"):
                # extract using QuadPoints if present
                qp = obj.get("/QuadPoints")
                if qp:
                    page_text_for_rect = f"QuadPoints={list(qp)}"
        except Exception:
            page_text_for_rect = ""

        if subtype is None:
            continue
        # Skip pure link annots without comment text
        if subtype == "/Link" and not contents:
            continue
        total += 1
        print(f"\n--- Page {i} | Annot #{total} ---")
        print(f"Subtype: {subtype}")
        if author:
            print(f"Author: {author}")
        if title:
            print(f"Title/Subject: {title}")
        if rect:
            print(f"Rect: {[float(x) for x in rect]}")
        if contents:
            print(f"Contents: {contents}")
        if page_text_for_rect:
            print(f"  {page_text_for_rect}")

print("=" * 80)
print(f"Total annotations: {total}")
