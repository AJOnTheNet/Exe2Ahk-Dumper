"""

AHKDumper V1.0.0 - Developed by AJ (https://github.com/AJOnTheNet)
Dumps strings from compiled AutoHotkey executables in various styles

Usage:
  python dumper.py compiled.exe
  python dumper.py myscript.exe --mode raw
  python dumper.py app.exe --mode decompile --group --with-offsets
  python dumper.py exe.exe --mode raw --only-gui --dedup > strings.txt

Note:
If you enable the “Add to PATH” option during installation, you can run this tool
from anywhere without specifying Python or the .py file.

Example:
  dumper myscript.exe --mode raw

Instead of:
  python dumper.py myscript.exe --mode raw

"""

import argparse
import sys
import re
import json
from pathlib import Path
from typing import List, Dict

try:
    import pefile
    HAS_PEFILE = True
except ImportError:
    HAS_PEFILE = False

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract & display strings from compiled AutoHotkey .exe files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""

Modes:
  raw          → clean list of strings only (default when no mode specified is decompile)
  decompile    → fake decompiler style with blocks & line-like numbers
  script-like  → attempt to look like AHK code fragments
  gui-only     → only GUI-related strings, bullet style

Examples:
  dumper.py myapp.exe --mode raw
  dumper.py script.exe --mode raw --with-offsets --dedup
  dumper.py exe.exe --mode decompile --group --min 6
  dumper.py app.exe --only-gui --json > gui_strings.json
        """
    )

    parser.add_argument("file", type=str, help="Path to compiled .exe")

    parser.add_argument("--min", "-n", type=int, default=5,
                        help="Minimum string length (default: 5)")

    parser.add_argument("--max", type=int, default=600,
                        help="Maximum string length (default: 600)")

    parser.add_argument("--mode", choices=["raw", "decompile", "script-like", "gui-only"],
                        default="decompile", help="Output style (default: decompile)")

    parser.add_argument("--encoding", "-e", default="auto",
                        help="Force encoding: utf-16le, utf-8, ascii (default: auto)")

    parser.add_argument("--dedup", action="store_true", help="Remove exact duplicates")

    parser.add_argument("--group", action="store_true",
                        help="Group related strings / add visual separation")

    parser.add_argument("--only-gui", action="store_true",
                        help="Filter to mostly GUI / dialog strings")

    parser.add_argument("--with-offsets", action="store_true",
                        help="Include hex offsets (in raw & decompile modes)")

    parser.add_argument("--with-context", type=int, default=0,
                        help="Show N bytes of surrounding context")

    parser.add_argument("--sections", action="store_true",
                        help="Show PE section names (requires pefile: pip install pefile)")

    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of text")

    parser.add_argument("--output", "-o", type=str,
                        help="Save to file instead of printing")

    parser.add_argument("--verbose", "-v", action="store_true")

    return parser.parse_args()


def detect_ahk_heuristic(raw: bytes) -> str:
    utf16_hits = len(re.findall(rb'[\x20-\x7E]\x00', raw))
    if utf16_hits > len(raw) // 35:
        return "likely AHK v2 / Unicode heavy"
    return "likely AHK v1 / mixed encoding"


def get_section_name(pe, offset: int) -> str:
    if not HAS_PEFILE or not pe:
        return ""
    try:
        for section in pe.sections:
            start = section.VirtualAddress + (pe.OPTIONAL_HEADER.ImageBase or 0)
            end = start + section.Misc_VirtualSize
            if start <= offset < end:
                return section.Name.decode(errors="ignore").rstrip("\x00").strip()
    except:
        pass
    return ""


def extract_strings(args) -> List[Dict]:
    path = Path(args.file)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    raw = path.read_bytes()
    size_mb = len(raw) / 1024 / 1024

    if args.verbose:
        print(f"File: {path.name}  •  {size_mb:.1f} MiB", file=sys.stderr)
        print(f"Version hint: {detect_ahk_heuristic(raw)}", file=sys.stderr)

    pe = None
    if args.sections and HAS_PEFILE:
        try:
            pe = pefile.PE(path=str(path))
        except Exception as e:
            print(f"PE parse failed: {e}", file=sys.stderr)

    wide_pat = re.compile(rb'((?:[\x20-\x7E\xA0-\xFF]\x00){' + str(args.min).encode() + rb',})')
    narrow_pat = re.compile(rb'([\x20-\x7E]{' + str(args.min).encode() + rb',})')

    candidates = []

    for m in wide_pat.finditer(raw):
        block = m.group(1)
        char_len = len(block) // 2
        if char_len > args.max:
            continue
        try:
            text = block.decode("utf-16le").rstrip("\x00")
        except:
            text = block.decode("utf-16le", errors="replace")
        if len(text.strip()) < args.min:
            continue
        candidates.append({
            "text": text,
            "enc": "utf-16le",
            "offset": m.start(),
            "len": char_len
        })

    for m in narrow_pat.finditer(raw):
        block = m.group(1)
        if len(block) > args.max:
            continue
        text = block.decode("ascii", errors="replace").rstrip("\x00")
        if len(text.strip()) < args.min:
            continue
        candidates.append({
            "text": text,
            "enc": "ascii/utf8",
            "offset": m.start(),
            "len": len(block)
        })

    candidates.sort(key=lambda x: x["offset"])

    if args.dedup:
        seen = set()
        candidates = [c for c in candidates if not (c["text"] in seen or seen.add(c["text"]))]

    if args.only_gui or args.mode == "gui-only":
        gui_kw = {
            "gui", "add", "show", "msgbox", "inputbox", "file", "select", "folder",
            "button", "edit", "text", "checkbox", "radio", "groupbox", "dropdownlist",
            "combobox", "listbox", "listview", "treeview", "statusbar", "tab", "monthcal",
            "slider", "progress", "hotkey", "datetime", "updown", "picture", "font", "color"
        }
        candidates = [
            c for c in candidates
            if any(k in c["text"].lower() for k in gui_kw)
               or re.search(r"[A-Z][a-z]{3,}", c["text"])
        ]

    for c in candidates:
        if args.sections:
            sec = get_section_name(pe, c["offset"])
            if sec:
                c["section"] = sec

        if args.with_context > 0:
            start = max(0, c["offset"] - args.with_context)
            end = min(len(raw), c["offset"] + 200 + args.with_context)
            ctx = raw[start:end].decode("utf-8", errors="replace")
            ctx = ctx.replace("\r", "␍").replace("\n", "␊")[:180]
            c["context"] = ctx

    return candidates


def format_raw(strings: List[Dict], args) -> str:
    lines = []

    if args.with_offsets:
        header = "  offset    | enc       | text"
        if args.sections:
            header += "   [section]"
        lines.extend([header, "──────────────────────────────────────────────"])

    prev_offset = -1000

    for s in strings:
        text = s["text"].replace("\r", "␍").replace("\n", "␊").replace("\t", "→").rstrip()

        if args.with_offsets:
            line = f"  0x{s['offset']:06X}  {s['enc']:<9}  {text}"
            if "section" in s:
                line += f"   [{s['section']}]"
            lines.append(line)

            if args.with_context > 0 and "context" in s:
                lines.append(f"                    ↳ {s['context']}")

        else:
            lines.append(text)
            if args.group:
                diff = s["offset"] - prev_offset
                if diff > 600:
                    lines.append("")

        prev_offset = s["offset"]

    return "\n".join(lines)


def format_decompile(strings: List[Dict], args) -> str:
    lines = [
        "",
        " ╔═════════════════════════════════════════════╗",
        " ║       AutoHotkey Decompiler Strings         ║",
        f"╚═════════════════════════════════════════════╝  ({len(strings)} found)",
        ""
    ]

    block_id = 0
    prev_offset = -1000

    for i, s in enumerate(strings, 1):
        diff = s["offset"] - prev_offset

        if args.group and (diff > 350 or i == 1):
            block_id += 1
            lines.append(f"┌─ Block #{block_id} ─ 0x{s['offset']:06X} ───────┐")
            lines.append("")

        prefix = f"  0x{s['offset']:06X} | {s['enc']:<9} | " if args.with_offsets else f"  {i:3d} | "
        text = s["text"].replace("\r", "␍").replace("\n", "␊").replace("\t", "→")
        line = prefix + text

        if "section" in s:
            line += f"  [{s['section']}]"

        lines.append(line)

        if args.with_context > 0 and "context" in s:
            lines.append(f"                ↳ {s['context'][:120]}")

        prev_offset = s["offset"]

    return "\n".join(lines)


def format_script_like(strings: List[Dict], args) -> str:
    lines = ["# Approximate AHK-like fragments (heuristic)", ""]
    block = []

    for s in strings:
        t = s["text"].strip()
        if not t:
            continue
        if t.endswith((":",";","}","{","⇒",")")) or t.startswith(("Gui", "Menu", "MsgBox", "InputBox", "FileSelect")):
            if block:
                lines.append("    " + " ".join(block))
                block = []
            lines.append(t)
        else:
            block.append(t)

    if block:
        lines.append("    " + " ".join(block))

    return "\n".join(lines)


def main():
    args = parse_args()

    strings = extract_strings(args)

    if not strings:
        print("No meaningful strings extracted.", file=sys.stderr)
        return

    if args.mode == "raw":
        output = format_raw(strings, args)

    elif args.mode == "decompile":
        output = format_decompile(strings, args)

    elif args.mode == "script-like":
        output = format_script_like(strings, args)

    elif args.mode == "gui-only":
        output = "\n".join(f"• {s['text']}" for s in strings)

    else:
        output = "Invalid mode"

    if args.json:
        data = {
            "file": args.file,
            "count": len(strings),
            "strings": [{k: v for k, v in s.items() if k not in ("raw",)} for s in strings]
        }
        output = json.dumps(data, indent=2, ensure_ascii=False)

    if args.output:
        try:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
            print(f"Saved {len(strings)} strings → {args.output}")
        except Exception as e:
            print(f"Write error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


if __name__ == "__main__":
    main()