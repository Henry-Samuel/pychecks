"""pychecks — Python code quality checks CLI.

Run multiple static checks on Python files: naming conventions,
docstring presence, function length, complexity hints, and more.
Zero runtime dependencies — stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------

class CheckResult(NamedTuple):
    file: str
    line: int
    code: str
    message: str


# ---------------------------------------------------------------------------
# AST-based checks
# ---------------------------------------------------------------------------

def _walk_files(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        if os.path.isfile(p):
            out.append(p)
        elif os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in files:
                    if f.endswith(".py"):
                        out.append(os.path.join(root, f))
    return sorted(out)


def _parse_file(path: str) -> ast.AST | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        return ast.parse(source, filename=path)
    except (SyntaxError, OSError):
        return None


def check_docstrings(tree: ast.AST | None, path: str) -> list[CheckResult]:
    """Flag functions/classes/modules missing docstrings."""
    results: list[CheckResult] = []
    if tree is None:
        return results

    if ast.get_docstring(tree) is None:
        results.append(CheckResult(path, 1, "D100", "Missing module docstring"))

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if ast.get_docstring(node) is None:
                results.append(
                    CheckResult(path, node.lineno, "D103", f"Missing function docstring: '{node.name}'")
                )
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if ast.get_docstring(node) is None:
                results.append(
                    CheckResult(path, node.lineno, "D103", f"Missing async function docstring: '{node.name}'")
                )
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if ast.get_docstring(node) is None:
                results.append(
                    CheckResult(path, node.lineno, "D101", "Missing class docstring")
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return results


def check_name_conventions(tree: ast.AST | None, path: str) -> list[CheckResult]:
    """Flag non-snake_case function/variable names."""
    results: list[CheckResult] = []
    if tree is None:
        return results

    def is_snake(name: str) -> bool:
        return bool(re.match(r"^[a-z_][a-z0-9_]*$", name))

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if not is_snake(node.name):
                results.append(
                    CheckResult(path, node.lineno, "N100", f"Function '{node.name}' not snake_case")
                )
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if not is_snake(node.name):
                results.append(
                    CheckResult(path, node.lineno, "N100", f"Async function '{node.name}' not snake_case")
                )
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                results.append(
                    CheckResult(path, node.lineno, "N101", f"Class '{node.name}' not CapWords")
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return results


def check_function_length(tree: ast.AST | None, path: str, max_lines: int = 30) -> list[CheckResult]:
    """Flag functions exceeding a line-count threshold."""
    results: list[CheckResult] = []
    if tree is None:
        return results

    class Visitor(ast.NodeVisitor):
        def _check(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            end = getattr(node, "end_lineno", node.lineno)
            length = end - node.lineno + 1
            if length > max_lines:
                results.append(
                    CheckResult(
                        path,
                        node.lineno,
                        "L100",
                        f"Function '{node.name}' is {length} lines (max {max_lines})",
                    )
                )

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._check(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._check(node)
            self.generic_visit(node)

    Visitor().visit(tree)
    return results


# ---------------------------------------------------------------------------
# Text-based checks
# ---------------------------------------------------------------------------

def check_trailing_whitespace(path: str) -> list[CheckResult]:
    """Flag trailing whitespace on any line."""
    results: list[CheckResult] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if line.rstrip("\n\r") != line.rstrip():
                    results.append(CheckResult(path, i, "W100", "Trailing whitespace"))
    except OSError:
        pass
    return results


def check_underscore_imports(path: str) -> list[CheckResult]:
    """Flag `from x import *` style imports."""
    results: list[CheckResult] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if re.match(r"^\s*from\s+\S+\s+import\s+\*$", line):
                    results.append(CheckResult(path, i, "I100", "Wildcard import"))
    except OSError:
        pass
    return results


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

CHECKERS = {
    "docstrings": check_docstrings,
    "names": check_name_conventions,
    "length": check_function_length,
    "trailing-whitespace": check_trailing_whitespace,
    "wildcard-imports": check_underscore_imports,
}


def run_checks(
    paths: list[str],
    *,
    checks: set[str] | None = None,
    max_function_lines: int = 30,
) -> list[CheckResult]:
    """Run selected checks across *paths* and return all results."""
    files = _walk_files(paths)
    selected = checks or set(CHECKERS.keys())
    results: list[CheckResult] = []

    for path in files:
        tree = _parse_file(path)
        for name in selected:
            checker = CHECKERS.get(name)
            if checker is None:
                continue
            if name in ("docstrings", "names", "length"):
                if tree is None:
                    continue
                kwargs: dict = {}
                if name == "length":
                    kwargs["max_lines"] = max_function_lines
                results.extend(checker(tree, path, **kwargs))
            else:
                results.extend(checker(path))

    results.sort(key=lambda r: (r.file, r.line, r.code))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pychecks",
        description="Python code quality checks — docstrings, naming, length, whitespace.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files or directories to check (default: current directory)",
    )
    parser.add_argument(
        "--check",
        action="append",
        dest="checks",
        choices=list(CHECKERS.keys()),
        help="Specific check to run. Can be repeated.",
    )
    parser.add_argument(
        "--max-function-lines",
        type=int,
        default=30,
        help="Max lines per function before flagging (default: 30)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args(argv)

    selected: set[str] | None = None
    if args.checks:
        selected = set(args.checks)

    results = run_checks(
        args.paths,
        checks=selected,
        max_function_lines=args.max_function_lines,
    )

    if args.json:
        import json
        out = [{"file": r.file, "line": r.line, "code": r.code, "message": r.message} for r in results]
        print(json.dumps(out, indent=2))
    else:
        if not results:
            print("pychecks: all checks passed")
        else:
            for r in results:
                print(f"{r.file}:{r.line}: {r.code} {r.message}")

    return 1 if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
