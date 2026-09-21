# pychecks — Python Code Quality Checks CLI

Run multiple static checks on Python files — docstring presence, naming conventions, function length, trailing whitespace, and wildcard imports. One command, zero runtime dependencies.

## Author

- **Name:** Henry Samuel
- **GitHub:** https://github.com/Henry-Samuel
- **Email:** 262435683+Henry-Samuel@users.noreply.github.com

## About

Quality matters, but running five different tools to catch naming problems, missing docs, and sloppy whitespace is tedious. `pychecks` bundles the checks teams actually care about into a single CLI — no plugins, no config files, no runtime dependencies. Point it at a file or a tree and get a sorted list of issues you can act on.

It is designed for pre-commit hooks, CI pipelines, and quick local reviews — not for enforcing a style guide line-by-line. It flags likely problems and leaves the fixing to you.

## Features

- **Docstring checks** — flag missing module, class, function, and async function docstrings (D100/D101/D103)
- **Naming convention checks** — enforce snake_case for functions, CapWords for classes (N100/N101)
- **Function length checks** — flag functions exceeding a configurable line threshold (L100)
- **Trailing whitespace detection** — catch stray spaces and tabs at end of line (W100)
- **Wildcard import detection** — flag `from x import *` style imports (I100)
- **AST-based analysis** — parses Python source with the standard library `ast` module for accurate results
- **File tree walking** — point at a directory and all `.py` files are checked recursively
- **JSON output mode** — `--json` flag produces machine-readable results for CI integration
- **Zero runtime dependencies** — stdlib only: `argparse`, `ast`, `os`, `re`, `sys`, `tempfile`, `json`

## Tech Stack

| Component | Details |
|-----------|---------|
| Language | Python 3.11+ |
| Dependencies | None (stdlib only) |
| Packaging | `pyproject.toml` with setuptools |
| Testing | `pytest` |
| Linting | `ruff` |
| Layout | Flat single-module (`pychecks.py`) |

## Project Structure

```
pychecks/
├── pychecks.py           # Main module (flat single-module layout)
├── pyproject.toml        # Packaging and metadata
├── README.md             # This file
├── .gitignore
└── tests/
    └── test_pychecks.py  # pytest suite
```

## Getting Started

### Install

```bash
pip install pychecks
```

### Check a directory

```bash
pychecks ./src
```

### Check specific files

```bash
pychecks module.py utils.py
```

### Run specific checks

```bash
pychecks --check docstrings --check names ./src
```

### Set function length threshold

```bash
pychecks --max-function-lines 50 ./src
```

### JSON output for CI

```bash
pychecks --json ./src > results.json
```

### Show help

```bash
pychecks --help
```

## Checks Reference

| Code | Check | Description |
|------|-------|-------------|
| D100 | Missing module docstring | Module has no docstring |
| D101 | Missing class docstring | Class has no docstring |
| D103 | Missing function docstring | Function has no docstring |
| N100 | Non-snake_case function | Function name not `snake_case` |
| N101 | Non-CapWords class | Class name not `CapWords` |
| L100 | Function too long | Function exceeds `--max-function-lines` |
| W100 | Trailing whitespace | Line ends with spaces or tabs |
| I100 | Wildcard import | `from x import *` detected |

## What pychecks does NOT do

- It does not enforce PEP 8 line length or formatting
- It does not check import ordering or unused imports
- It does not analyze cyclomatic complexity
- It does not modify files — it only reports issues

## Topics

`python`, `cli`, `code-quality`, `lint`, `docstrings`, `naming-conventions`, `stdlib`, `static-analysis`, `dev-tool`

## License

MIT
