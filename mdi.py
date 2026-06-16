#!/usr/bin/env python3
"""
mdi — minimal terminal markdown renderer
usage: mdi file.md
       cat file.md | mdi
       mdi  (opens interactive input)
"""

import sys
import re
import os
import shutil

COLS = shutil.get_terminal_size((80, 24)).columns

# ANSI codes
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
ITALIC = "\033[3m"
UL     = "\033[4m"

FG_GREEN  = "\033[32m"
FG_CYAN   = "\033[36m"
FG_YELLOW = "\033[33m"
FG_BLUE   = "\033[34m"
FG_MAGENTA= "\033[35m"
FG_RED    = "\033[31m"
BG_DARK   = "\033[48;5;236m"
FG_WHITE  = "\033[97m"

def no_ansi(s):
    return re.sub(r'\033\[[0-9;]*m', '', s)

def visible_len(s):
    return len(no_ansi(s))

def hrule(char="─", color=DIM):
    return color + char * COLS + RESET

def wrap(text, width, indent=""):
    words = text.split(" ")
    lines = []
    line = indent
    for w in words:
        if visible_len(line) + visible_len(w) + 1 > width and line.strip():
            lines.append(line.rstrip())
            line = indent + w + " "
        else:
            line += w + " "
    if line.strip():
        lines.append(line.rstrip())
    return lines

def inline(text):
    """Apply inline formatting: bold, italic, code, links."""
    # inline code
    text = re.sub(r'`([^`]+)`',
        lambda m: BG_DARK + FG_WHITE + " " + m.group(1) + " " + RESET, text)
    # bold+italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', BOLD + ITALIC + r'\1' + RESET, text)
    # bold
    text = re.sub(r'\*\*(.+?)\*\*', BOLD + r'\1' + RESET, text)
    text = re.sub(r'__(.+?)__',     BOLD + r'\1' + RESET, text)
    # italic
    text = re.sub(r'\*(.+?)\*', ITALIC + r'\1' + RESET, text)
    text = re.sub(r'_(.+?)_',   ITALIC + r'\1' + RESET, text)
    # strikethrough
    text = re.sub(r'~~(.+?)~~', DIM + r'\1' + RESET, text)
    # links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: UL + FG_BLUE + m.group(1) + RESET + DIM + " (" + m.group(2) + ")" + RESET, text)
    # bare urls
    text = re.sub(r'(?<!\()(https?://\S+)', UL + FG_BLUE + r'\1' + RESET, text)
    return text

def render(md_text):
    lines = md_text.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # --- fenced code block ---
        if re.match(r'^```', line):
            lang = line[3:].strip()
            i += 1
            code_lines = []
            while i < len(lines) and not re.match(r'^```', lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            label = (" " + lang.upper() if lang else "")
            out.append(FG_CYAN + DIM + "┌─" + label + ("─" * (COLS - 3 - len(label))) + RESET)
            for cl in code_lines:
                padded = cl.replace("\t", "    ")
                out.append(FG_CYAN + DIM + "│" + RESET + " " + FG_WHITE + DIM + padded + RESET)
            out.append(FG_CYAN + DIM + "└" + "─" * (COLS - 1) + RESET)
            continue

        # --- headings ---
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            text  = inline(m.group(2))
            if level == 1:
                out.append("")
                out.append(BOLD + FG_GREEN + text + RESET)
                out.append(FG_GREEN + DIM + "═" * min(visible_len(no_ansi(text)) + 2, COLS) + RESET)
            elif level == 2:
                out.append("")
                out.append(BOLD + FG_CYAN + text + RESET)
                out.append(FG_CYAN + DIM + "─" * min(visible_len(no_ansi(text)) + 1, COLS) + RESET)
            elif level == 3:
                out.append("")
                out.append(BOLD + FG_YELLOW + "▸ " + text + RESET)
            else:
                out.append(BOLD + DIM + "  " + text + RESET)
            i += 1
            continue

        # --- horizontal rule ---
        if re.match(r'^(\s*[-*_]){3,}\s*$', line):
            out.append(hrule())
            i += 1
            continue

        # --- blockquote ---
        if line.startswith(">"):
            text = line.lstrip("> ").strip()
            wrapped = wrap(inline(text), COLS - 4, "  ")
            for wl in wrapped:
                out.append(FG_MAGENTA + "▌ " + RESET + DIM + wl + RESET)
            i += 1
            continue

        # --- unordered list ---
        m = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if m:
            indent_lvl = len(m.group(1)) // 2
            bullet = ["•", "◦", "▪"][min(indent_lvl, 2)]
            text = inline(m.group(2))
            prefix = "  " * indent_lvl + FG_GREEN + bullet + RESET + " "
            wrapped = wrap(text, COLS - 4 - indent_lvl * 2, "    " + "  " * indent_lvl)
            if wrapped:
                out.append("  " * indent_lvl + FG_GREEN + bullet + RESET + " " + wrapped[0].lstrip())
                for wl in wrapped[1:]:
                    out.append(wl)
            i += 1
            continue

        # --- ordered list ---
        m = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
        if m:
            indent_lvl = len(m.group(1)) // 2
            num = m.group(2)
            text = inline(m.group(3))
            prefix_len = len(num) + 2 + indent_lvl * 2
            wrapped = wrap(text, COLS - prefix_len - 2, " " * (prefix_len + 2))
            if wrapped:
                out.append("  " * indent_lvl + FG_YELLOW + num + "." + RESET + " " + wrapped[0].lstrip())
                for wl in wrapped[1:]:
                    out.append(wl)
            i += 1
            continue

        # --- table ---
        if "|" in line and i + 1 < len(lines) and re.match(r'^\|?[\s\-|:]+\|', lines[i + 1]):
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) >= 2:
                rows = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                    rows.append(cells)
                sep_idx = next((j for j, r in enumerate(rows) if all(re.match(r'^[-:]+$', c.replace(" ","")) for c in r if c)), 1)
                header = rows[:sep_idx]
                body   = rows[sep_idx + 1:]
                cols_data = header + body
                if cols_data:
                    ncols = max(len(r) for r in cols_data)
                    col_w = [(max(len(no_ansi(r[c])) if c < len(r) else 0 for r in cols_data) + 2) for c in range(ncols)]
                    def fmt_row(row, bold=False):
                        cells = []
                        for ci, cw in enumerate(col_w):
                            val = row[ci] if ci < len(row) else ""
                            rendered = inline(val)
                            pad = cw - len(no_ansi(rendered))
                            cell = (BOLD if bold else "") + rendered + (RESET if bold else "") + " " * pad
                            cells.append(cell)
                        return DIM + "│" + RESET + (DIM + "│" + RESET).join(" " + c for c in cells) + DIM + "│" + RESET
                    div = DIM + "├" + "┼".join("─" * (cw + 1) for cw in col_w) + "┤" + RESET
                    top = DIM + "┌" + "┬".join("─" * (cw + 1) for cw in col_w) + "┐" + RESET
                    bot = DIM + "└" + "┴".join("─" * (cw + 1) for cw in col_w) + "┘" + RESET
                    out.append(top)
                    for j, row in enumerate(header):
                        out.append(fmt_row(row, bold=True))
                    out.append(div)
                    for row in body:
                        out.append(fmt_row(row))
                    out.append(bot)
            continue

        # --- blank line ---
        if line.strip() == "":
            out.append("")
            i += 1
            continue

        # --- paragraph ---
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() != "" and not re.match(r'^[#>`\-*+]|^\d+\.|\|', lines[i]):
            para.append(lines[i])
            i += 1
        full = " ".join(para)
        for wl in wrap(inline(full), COLS):
            out.append(wl)
        out.append("")

    return "\n".join(out)

def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if path in ("-h", "--help"):
            print(f"{BOLD}mdi{RESET} — minimal markdown renderer\n")
            print(f"  {FG_GREEN}mdi file.md{RESET}          render a file")
            print(f"  {FG_GREEN}cat file.md | mdi{RESET}    pipe markdown")
            print(f"  {FG_GREEN}mdi{RESET}                  interactive mode")
            sys.exit(0)
        try:
            with open(path, "r") as f:
                md = f.read()
        except FileNotFoundError:
            print(f"{FG_RED}error:{RESET} file not found: {path}", file=sys.stderr)
            sys.exit(1)
    elif not sys.stdin.isatty():
        md = sys.stdin.read()
    else:
        print(f"{BOLD}mdi{RESET} {DIM}interactive — paste markdown, then Ctrl+D to render{RESET}")
        try:
            md = sys.stdin.read()
        except KeyboardInterrupt:
            sys.exit(0)

    print(render(md))

if __name__ == "__main__":
    main()