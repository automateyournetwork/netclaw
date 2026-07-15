#!/usr/bin/env python3
"""Minimal, dependency-free markdown-to-ANSI renderer for the netclaw TUI.

Handles just the subset that shows up in N2N chat replies: **bold**, `code`,
#/## headings, "=== TITLE ===" section markers, --- rules, and pipe tables.
Reads markdown-ish text on stdin, writes ANSI-formatted text to stdout.
"""
import re
import sys

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[38;5;45m"
NC = "\033[0m"

INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
INLINE_CODE = re.compile(r"`([^`]+)`")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
SECTION = re.compile(r"^===+\s*(.*?)\s*===+$")
RULE = re.compile(r"^[-_*]{3,}$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
SEP_CELL = re.compile(r"^:?-+:?$")


def inline(text):
    text = INLINE_BOLD.sub(lambda m: f"{BOLD}{m.group(1)}{NC}", text)
    text = INLINE_CODE.sub(lambda m: f"{CYAN}{m.group(1)}{NC}", text)
    return text


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def render_table(rows):
    is_sep = lambda cells: cells and all(SEP_CELL.match(c or "-") for c in cells)
    parsed = [split_row(r) for r in rows]
    header = None
    body = []
    for cells in parsed:
        if is_sep(cells):
            continue
        if header is None:
            header = cells
        else:
            body.append(cells)
    if header is None:
        return "\n".join(rows)
    ncols = len(header)
    widths = [len(header[i]) if i < len(header) else 0 for i in range(ncols)]
    for row in body:
        for i in range(ncols):
            cell = row[i] if i < len(row) else ""
            widths[i] = max(widths[i], len(cell))
    out = []

    def fmt(cells, bold=False):
        parts = []
        for i in range(ncols):
            cell = cells[i] if i < len(cells) else ""
            pad = cell.ljust(widths[i])
            parts.append(f"{BOLD}{pad}{NC}" if bold else pad)
        return "  " + (f" {DIM}│{NC} ").join(parts)

    out.append(fmt(header, bold=True))
    out.append(f"  {DIM}" + "─┼─".join("─" * w for w in widths) + f"{NC}")
    for row in body:
        out.append(fmt(row))
    return "\n".join(out)


def render(text):
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = SECTION.match(line.strip())
        if m:
            out.append(f"{BOLD}{CYAN}{line.strip()}{NC}")
            i += 1
            continue
        m = HEADING.match(line)
        if m:
            out.append(f"{BOLD}{CYAN}{m.group(2)}{NC}")
            i += 1
            continue
        if RULE.match(line.strip()):
            out.append(f"{DIM}{'─' * 60}{NC}")
            i += 1
            continue
        if TABLE_ROW.match(line):
            block = []
            while i < len(lines) and TABLE_ROW.match(lines[i]):
                block.append(lines[i])
                i += 1
            out.append(render_table(block))
            continue
        out.append(inline(line))
        i += 1
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout.write(render(sys.stdin.read()))
