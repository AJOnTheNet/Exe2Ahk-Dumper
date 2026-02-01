# AHKDumper — AutoHotkey string recovery helper

**AHKDumper** extracts and organizes printable strings from executables produced by **AJ** to help people reconstruct AutoHotkey scripts.
It is *not* a full decompiler — it surfaces likely script strings (hotkeys, GUI labels, MsgBox text, paths, etc.) and provides several output modes and filters to make manual reconstruction practical.

**Author:** AJ — [https://github.com/AJOnTheNet](https://github.com/AJOnTheNet)
**Version:** 1.0.0

---

## Table of contents

* [Why this exists](#why-this-exists)
* [Quick start](#quick-start)
* [Installation](#installation)

  * [Requirements](#requirements)
  * [Install from source (recommended)](#install-from-source-recommended)
  * [Windows installer: `installer.bat`](#windows-installer-installerbat)
* [Usage](#usage)

  * [Basic examples](#basic-examples)
  * [All flags (explanations)](#all-flags-explanations)
  * [Modes explained](#modes-explained)
* [How it works (internals)](#how-it-works-internals)
* [Reading the output — tips & gotchas](#reading-the-output--tips--gotchas)
* [Troubleshooting](#troubleshooting)
* [Security, legality & ethics](#security-legality--ethics)
* [Contributing](#contributing)
* [Changelog](#changelog)
* [License & credits](#license--credits)

---

# Why this exists

Compiled AutoHotkey executables produced by Ahk2Exe typically embed the runtime/interpreter and your script (often as UTF-16LE or compressed). That means a raw `strings` dump is noisy: the interpreter contributes thousands of benign "internal" strings and your script strings are mixed among them.

AHKDumper organizes and filters extracted strings with AHK-aware heuristics so you can find the meaningful bits quickly — hotkeys, dialog text, file paths, command names — and then manually reconstruct the script. It intentionally **does not** claim to magically decompile logic or rebuild control flow.

---

# Quick start

Clone or download the repo, then:

```bash
# minimal example — run from repo folder
python dumper.py path\to\compiled.exe --mode decompile

# if installed to PATH (optional installer)
dumper path\to\compiled.exe --mode script-like --only-gui
```

If you used the included Windows installer and chose **Add to PATH**, you can call `dumper` everywhere (see [Installer notes](#windows-installer-installerbat)).

---

# Installation

## Requirements

AHKDumper is intentionally minimal. It uses the Python standard library for everything except optional PE section parsing.

* Python 3.8+ (recommended)
* Optional package: `pefile` (only required if you want PE section names displayed)

**assets/requirements.txt**

```text
pefile
```

> NOTE: Standard-library modules like `argparse`, `pathlib`, `re`, `json`, and `typing` are used — they are built-in and should **not** be placed in `requirements.txt`.

## Install from source (recommended)

1. Ensure Python 3 is installed and on `PATH`.
2. From the project root:

```bash
python -m pip install --upgrade pip
python -m pip install -r assets/requirements.txt  # optional, for section display
```

3. Run:

```bash
python dumper.py compiled.exe --mode decompile
```

## Windows installer: `installer.bat`

An `installer.bat` is included to simplify setup. It will:

* Install Python dependencies from `assets\requirements.txt`.
* Offer to add the tool to `PATH`. If the user chooses system PATH, the installer will request admin privileges (UAC) and then update the system `PATH`.
* Create a simple launcher shim `dumper.bat` in the install directory so `dumper` can be run without `python dumper.py`.

Important notes:

* If you add to PATH at the system level, the script requests elevation (re-launches itself as admin). This is safe and expected behaviour on Windows.
* `setx` or registry PATH modifications require opening a *new* terminal to take effect.
* Installer will not silently modify PATH without your confirmation.

---

# Usage

## Basic examples

```bash
# default decompile-style output
python dumper.py myapp.exe

# raw string list (machine-friendly)
python dumper.py myapp.exe --mode raw > strings.txt

# only GUI-like strings (MsgBox, Gui Add, labels, etc.)
python dumper.py myapp.exe --mode gui-only --only-gui

# decompile-like output with offsets and section names (requires pefile)
python dumper.py myapp.exe --mode decompile --with-offsets --sections

# deduplicate exact duplicates and group nearby strings
python dumper.py myapp.exe --dedup --group
```

If installed to PATH via the installer:

```bash
# same as above, but without python
dumper myapp.exe --mode script-like --with-offsets
```

## All flags (explanations)

```
file                    Path to compiled .exe (positional argument)

--min, -n INT           Minimum printable string length (default: 5)
--max INT               Maximum string length (default: 600)
--mode {raw,decompile,script-like,gui-only}
                        Output style (default: decompile)
--encoding, -e STR      Force encoding (utf-16le, utf-8, ascii, auto)
--dedup                 Remove exact duplicates
--group                 Group related strings / add visual separation
--only-gui              Filter to mostly GUI / dialog strings
--with-offsets          Include hex offsets (raw & decompile modes)
--with-context INT      Show N bytes of surrounding context
--sections              Show PE section names (requires pefile)
--json                  Output JSON instead of text
--output, -o FILE       Save output to file instead of printing
--verbose, -v           Verbose progress/info
```

## Modes explained

* **raw** — plain list of extracted printable strings (machine-friendly). Useful when you want to pipe into other tools or grep.
* **decompile** (default) — human-friendly, pseudo-decompiler layout: blocks, offsets, counts, and optional section names. Great for manual review.
* **script-like** — tries to combine strings into AHK-like fragments and prints them in a more code-like shape.
* **gui-only** — filters output toward GUI-related strings (Gui Add, MsgBox text, labels, etc.).

---

# How it works (internals)

AHKDumper follows a pragmatic, staged pipeline:

1. **Read raw bytes** from the supplied EXE.
2. **Search for printable strings** using two patterns:

   * UTF-16LE wide-character sequences (common for AHK scripts embedded as Unicode).
   * ASCII/UTF-8 narrow-character sequences.
3. **Decode and collect** candidate strings with metadata:

   * decoded `text`
   * `enc` (utf-16le or ascii/utf8)
   * `offset` (byte offset inside the file)
   * `len` (character or byte length)
4. **Filter & score** candidates using heuristics:

   * minimum/maximum length
   * deduplication (if requested)
   * GUI keyword filtering (if `--only-gui`)
   * grouping nearby offsets to suggest logical blocks
5. **Optional section lookup** (requires `pefile`): map offsets to PE section names and include them in output.
6. **Format** according to `--mode` and output to console or file.

Key design decisions:

* Avoid false promises: this is *string recovery + heuristics*, not logic decompilation.
* Keep external dependencies to a minimum (only `pefile` optionally).
* Provide multiple output styles for both human and machine workflows.

---

# Reading the output — tips & gotchas

A lot of confusion comes from the fact that **compiled AHK binaries embed the runtime**. Expect thousands of internal strings before useful script strings appear. Use these tactics to be effective:

### Quick tips

* Use `--group` to visually separate clusters of related strings (helps find script blocks).
* Use `--only-gui` to focus on GUI/dialog-related strings (MsgBox, labels, buttons).
* Use `--mode script-like` to get AHK-like fragments that are easier to scan.
* Use `--with-offsets` to see where strings live in the binary (helps cluster related items).
* Pipe to file and search: `python dumper.py app.exe --mode raw > out.txt` and `grep`/search locally.

### Helpful header printed by the tool

The tool prints a short `[INFO]` block when verbose — e.g. `Likely encoding: Unicode-heavy` — to set expectations that many strings are runtime artifacts.

### Why the first N lines look like garbage

This is normal. The AHK interpreter/runtime and linked libraries include many internal strings (error messages, API names, module identifiers). The user script strings are generally mixed in; they can appear *later* or interleaved.

---

# Troubleshooting

### Python not found

```
[ERROR] Python is not installed or not in PATH.
```

Install Python 3.8+ and ensure `python` is on your PATH.

### `pefile` missing

You will still be able to run AHKDumper without `pefile`. Install it if you want section names:

```bash
python -m pip install pefile
```

### PATH changes not visible

When the installer modifies PATH (user or system), open a **new terminal** for changes to apply.

### Installer fails to add to system PATH

If you selected system PATH, the installer must re-run elevated. You will see a UAC prompt — allow it to continue. If UAC is declined, the installer will skip system PATH modification.

### Antivirus false positives

Some Windows AVs are pickier about unpacked tools. If you see warnings, inspect the files, and consider packaging using PyInstaller and signing, or distribute via GitHub releases with clear checksums.

### Encoding oddities

Some strings may contain replacement characters if the binary uses non-UTF encodings or compressed stores. `--encoding` can be forced, but `auto` works for most cases.

---

# Security, legality & ethics

AHKDumper is a forensic/recovery aid. You must only use it on executables you own, have permission to analyze, or which fall under an allowed auditing scope.

**Do not** use this tool to bypass licensing, access control, or to extract private scripts without explicit permission. The author disclaims liability for misuse.

---

# Contributing

Want to help? Great.

Suggested contribution areas:

* Improve GUI string heuristics
* Improve scoring and noise suppression
* Add optional colored CLI output (make it opt-in)
* Add tests with known Ahk2Exe samples
* Port to a small binary (PyInstaller) and add CI builds

To contribute:

1. Fork the repo
2. Create a branch for your feature/fix
3. Open a PR with a clear description and test cases

If you add features, please keep the standard-library-first philosophy where possible.

---

# Changelog

## v1.0.0

* Initial public release
* UTF-16LE + ASCII string extraction
* Modes: `raw`, `decompile`, `script-like`, `gui-only`
* Options: `--group`, `--dedup`, `--with-offsets`, `--sections` (pefile)
* Windows `installer.bat` with optional PATH setup and elevation flow

---

# License & credits

```
MIT License
Copyright (c) 2026 AJ
```

This repo was developed by **AJ** — [https://github.com/AJOnTheNet](https://github.com/AJOnTheNet)

If you prefer a different license, change the `LICENSE` file accordingly.