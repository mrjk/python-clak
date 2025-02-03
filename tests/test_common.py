import pytest
from clak.common import deindent_docstring

pytestmark = pytest.mark.tags("unit-tests")

def test_deindent_docstring_empty():
    """Test deindenting an empty string."""
    assert deindent_docstring("") == ""


def test_deindent_docstring_single_line():
    """Test deindenting a single line string."""
    assert deindent_docstring("Hello world") == "Hello world"


def test_deindent_docstring_no_indent():
    """Test deindenting a multiline string with no indentation."""
    text = """First line
Second line
Third line"""
    assert deindent_docstring(text) == text


def test_deindent_docstring_with_indent():
    """Test deindenting a properly indented docstring."""
    text = """
    First line
    Second line
        Indented line
    Third line"""
    expected = """
First line
Second line
    Indented line
Third line"""
    assert deindent_docstring(text) == expected


def test_deindent_docstring_mixed_indent():
    """Test deindenting with mixed indentation levels."""
    text = """
    First line
  Second line
      Third line"""
    expected = """
First line
  Second line
  Third line"""  # Only first line indent is used as reference
    assert deindent_docstring(text) == expected


def test_deindent_docstring_with_reindent():
    """Test deindenting and then reindenting with a new prefix."""
    text = """
    First line
    Second line
        Indented line"""
    expected = """
  First line
  Second line
      Indented line"""
    assert deindent_docstring(text, reindent="  ") == expected


def test_deindent_docstring_tabs():
    """Test deindenting with tab characters."""
    text = """
\tFirst line
\tSecond line
\t\tIndented line"""
    expected = """
First line
Second line
\tIndented line"""
    assert deindent_docstring(text) == expected


def test_deindent_docstring_no_reindent():
    """Test that reindent=False doesn't modify the text."""
    text = """
    First line
    Second line"""
    expected = """
First line
Second line"""
    assert deindent_docstring(text, reindent=False) == expected 