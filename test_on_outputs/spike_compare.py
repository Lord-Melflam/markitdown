#!/usr/bin/env python3
"""Side-by-side spike: current MarkItDown PDF converter vs PyMuPDF4LLM.

Runs both on the same PDF, writes each output to disk, and prints a
structure-preservation scorecard so you can see what each keeps.

Usage:
    .venv/bin/python test_on_outputs/spike_compare.py [path-to.pdf]
"""

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_PDF = HERE / "LINFO2347_All_courses_2026_compressed.pdf"


def metrics(md: str) -> dict:
    lines = md.splitlines()
    return {
        "total lines": len(lines),
        "chars": len(md),
        "MD headings (#..)": sum(bool(re.match(r"^#{1,6}\s", ln)) for ln in lines),
        "MD bullets (-/*/+)": sum(bool(re.match(r"^\s*[-*+]\s", ln)) for ln in lines),
        "MD ordered (1.)": sum(bool(re.match(r"^\s*\d+[.)]\s", ln)) for ln in lines),
        "literal bullet glyphs": len(re.findall(r"[•▪‣◦]", md)),
        "table pipe lines": sum(ln.count("|") > 1 for ln in lines),
        "image refs ![]()": len(re.findall(r"!\[[^\]]*\]\(", md)),
        "bold/italic (**)": len(re.findall(r"\*\*[^*]+\*\*", md)),
    }


def run_markitdown(pdf: Path) -> str:
    from markitdown import MarkItDown

    md = MarkItDown()
    return md.convert(str(pdf)).text_content


def run_pymupdf4llm(pdf: Path) -> str:
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf))


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf.exists():
        sys.exit(f"PDF not found: {pdf}")

    print(f"Input: {pdf.name} ({pdf.stat().st_size / 1e6:.1f} MB)\n")

    runners = {
        "markitdown (current)": (run_markitdown, HERE / "spike_markitdown.md"),
        "pymupdf4llm": (run_pymupdf4llm, HERE / "spike_pymupdf4llm.md"),
    }

    results = {}
    for name, (fn, out) in runners.items():
        t0 = time.perf_counter()
        text = fn(pdf)
        dt = time.perf_counter() - t0
        out.write_text(text)
        results[name] = (metrics(text), dt, out)
        print(f"✓ {name}: {dt:.1f}s → {out.name}")

    # Scorecard
    keys = list(next(iter(results.values()))[0].keys())
    names = list(results.keys())
    width = max(len(k) for k in keys) + 2
    colw = 22
    print("\n" + "STRUCTURE SCORECARD".center(width + colw * len(names)))
    print("-" * (width + colw * len(names)))
    print("metric".ljust(width) + "".join(n[:colw - 1].ljust(colw) for n in names))
    print("-" * (width + colw * len(names)))
    for k in keys:
        row = k.ljust(width)
        for n in names:
            row += str(results[n][0][k]).ljust(colw)
        print(row)
    print("-" * (width + colw * len(names)))
    row = "time (s)".ljust(width)
    for n in names:
        row += f"{results[n][1]:.1f}".ljust(colw)
    print(row)


if __name__ == "__main__":
    main()
