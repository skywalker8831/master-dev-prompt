import pytest

from slugify import slugify


def test_basic_two_word_name():
    assert slugify("Acme Corporation") == "acme-corporation"


def test_lowercases_input():
    assert slugify("UPPER CASE") == "upper-case"


def test_replaces_special_characters_with_hyphens():
    assert slugify("Hello_World!") == "hello-world"


def test_collapses_multiple_separators():
    assert slugify("foo  --  bar") == "foo-bar"


def test_strips_leading_and_trailing_hyphens():
    assert slugify("  My  Enterprise! ") == "my-enterprise"


def test_preserves_numbers():
    assert slugify("Hello_World 2024") == "hello-world-2024"


def test_single_word():
    assert slugify("github") == "github"


def test_already_valid_slug():
    assert slugify("my-enterprise") == "my-enterprise"


def test_empty_string():
    assert slugify("") == ""


def test_only_special_characters():
    assert slugify("!!!") == ""
