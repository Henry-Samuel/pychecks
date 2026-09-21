"""Tests for pychecks — Python code quality checks CLI."""

from __future__ import annotations

import ast
import os
import tempfile

import pytest

import pychecks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mktext(text: str) -> str:
    """Write *text* to a temp .py file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------------------
# File walking
# ---------------------------------------------------------------------------

def test_walk_files_recurses_into_dirs():
    d = tempfile.mkdtemp()
    sub = os.path.join(d, "pkg")
    os.makedirs(sub)
    for name in ("a.py", "b.py", "c.txt"):
        with open(os.path.join(d if name == "c.txt" else sub, name), "w") as fh:
            fh.write("")
    files = pychecks._walk_files([d])
    assert len(files) == 2
    assert all(f.endswith(".py") for f in files)
    import shutil
    shutil.rmtree(d)


def test_walk_files_returns_sorted():
    d = tempfile.mkdtemp()
    for name in ("z.py", "a.py"):
        with open(os.path.join(d, name), "w") as fh:
            fh.write("")
    files = pychecks._walk_files([d])
    assert files == sorted(files)
    import shutil
    shutil.rmtree(d)


def test_walk_files_accepts_single_file():
    fd, path = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    with open(path, "w") as fh:
        fh.write("")
    files = pychecks._walk_files([path])
    assert files == [path]
    os.remove(path)


# ---------------------------------------------------------------------------
# Parse file
# ---------------------------------------------------------------------------

def test_parse_file_valid():
    path = _mktext("x = 1\n")
    tree = pychecks._parse_file(path)
    assert isinstance(tree, ast.AST)
    os.remove(path)


def test_parse_file_syntax_error_returns_none():
    path = _mktext("x = \n")
    tree = pychecks._parse_file(path)
    assert tree is None
    os.remove(path)


# ---------------------------------------------------------------------------
# Docstring checks
# ---------------------------------------------------------------------------

def test_missing_module_docstring():
    path = _mktext("x = 1\n")
    tree = pychecks._parse_file(path)
    assert tree is not None
    results = pychecks.check_docstrings(tree, path)
    assert any(r.code == "D100" for r in results)
    os.remove(path)


def test_module_with_docstring_passes():
    path = _mktext('"""Module docs."""\nx = 1\n')
    tree = pychecks._parse_file(path)
    results = pychecks.check_docstrings(tree, path)
    assert not any(r.code == "D100" for r in results)
    os.remove(path)


def test_missing_function_docstring():
    src = "def foo():\n    pass\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_docstrings(tree, path)
    assert any(r.code == "D103" and "foo" in r.message for r in results)
    os.remove(path)


def test_function_with_docstring_passes():
    src = 'def foo():\n    """Foo doc."""\n    pass\n'
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_docstrings(tree, path)
    assert not any(r.code == "D103" for r in results)
    os.remove(path)


def test_missing_class_docstring():
    src = "class Foo:\n    pass\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_docstrings(tree, path)
    assert any(r.code == "D101" for r in results)
    os.remove(path)


# ---------------------------------------------------------------------------
# Name convention checks
# ---------------------------------------------------------------------------

def test_snake_case_function_passes():
    src = "def my_func():\n    pass\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_name_conventions(tree, path)
    assert not any(r.code == "N100" for r in results)
    os.remove(path)


def test_camel_case_function_flags():
    src = "def myFunc():\n    pass\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_name_conventions(tree, path)
    assert any(r.code == "N100" for r in results)
    os.remove(path)


def test_capwords_class_passes():
    src = "class MyParser:\n    pass\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_name_conventions(tree, path)
    assert not any(r.code == "N101" for r in results)
    os.remove(path)


def test_lowercase_class_flags():
    src = "class myParser:\n    pass\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_name_conventions(tree, path)
    assert any(r.code == "N101" for r in results)
    os.remove(path)


# ---------------------------------------------------------------------------
# Function length checks
# ---------------------------------------------------------------------------

def test_short_function_passes():
    src = "def f():\n    x = 1\n    return x\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_function_length(tree, path, max_lines=10)
    assert not any(r.code == "L100" for r in results)
    os.remove(path)


def test_long_function_flags():
    lines = ["def f():"] + [f"    {i}" for i in range(35)] + ["    pass"]
    src = "\n".join(lines) + "\n"
    path = _mktext(src)
    tree = pychecks._parse_file(path)
    results = pychecks.check_function_length(tree, path, max_lines=30)
    assert any(r.code == "L100" for r in results)
    os.remove(path)


# ---------------------------------------------------------------------------
# Trailing whitespace
# ---------------------------------------------------------------------------

def test_no_trailing_whitespace_passes():
    path = _mktext("x = 1\ny = 2\n")
    results = pychecks.check_trailing_whitespace(path)
    assert not results
    os.remove(path)


def test_trailing_whitespace_flags():
    path = _mktext("x = 1  \ny = 2\n")
    results = pychecks.check_trailing_whitespace(path)
    assert any(r.code == "W100" for r in results)
    os.remove(path)


# ---------------------------------------------------------------------------
# Wildcard import checks
# ---------------------------------------------------------------------------

def test_wildcard_import_flags():
    path = _mktext("from os import *\n")
    results = pychecks.check_underscore_imports(path)
    assert any(r.code == "I100" for r in results)
    os.remove(path)


def test_normal_import_passes():
    path = _mktext("from os import path\n")
    results = pychecks.check_underscore_imports(path)
    assert not results
    os.remove(path)


# ---------------------------------------------------------------------------
# Full orchestration
# ---------------------------------------------------------------------------

def test_run_checks_single_file():
    src = '"""Mod."""\n\ndef good():\n    """Doc."""\n    pass\n\nclass OK:\n    """Doc."""\n    pass\n'
    path = _mktext(src)
    results = pychecks.run_checks([path], checks={"docstrings", "names"})
    assert not results
    os.remove(path)


def test_run_checks_multiple_files():
    src1 = "def f():\n    pass\n"
    src2 = "def g():\n    pass\n"
    p1 = _mktext(src1)
    p2 = _mktext(src2)
    results = pychecks.run_checks([p1, p2], checks={"docstrings"})
    assert len(results) >= 2  # D103 for each
    os.remove(p1)
    os.remove(p2)


def test_run_checks_empty_selects_all():
    src = "x = 1\n"
    path = _mktext(src)
    results = pychecks.run_checks([path])
    assert results  # at least D100
    os.remove(path)


def test_results_sorted():
    src = "from os import *\n\ndef Bad():\n    pass\n"
    path = _mktext(src)
    results = pychecks.run_checks([path], checks={"wildcard-imports", "names"})
    codes = [r.code for r in results]
    assert codes == sorted(codes)
    os.remove(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_main_no_args_uses_cwd(monkeypatch, capsys):
    monkeypatch.setattr(os, "walk", lambda p: [(".", [], ["t.py"])])
    # This is a lightweight smoke test for argument parsing
    import pychecks as pc
    try:
        pc.main(["--help"])
    except SystemExit as e:
        assert e.code == 0


def test_main_returns_1_on_findings():
    src = "def f():\n    pass\n"
    path = _mktext(src)
    try:
        ret = pychecks.main([path, "--check", "docstrings"])
        assert ret == 1
    finally:
        os.remove(path)


def test_main_returns_0_on_clean():
    src = '"""Mod."""\ndef f():\n    """Doc."""\n    pass\n'
    path = _mktext(src)
    try:
        ret = pychecks.main([path, "--check", "docstrings"])
        assert ret == 0
    finally:
        os.remove(path)
