"""
slugify.py — Utility for generating GitHub Enterprise URL slugs.

A slug is the URL-friendly identifier that appears in an enterprise's web
address, e.g. https://github.com/enterprises/your-slug.

The GitHub GraphQL API uses the slug as the argument to the enterprise query:

    query($slug: String!) {
      enterprise(slug: $slug) {
        name
        id
        members { totalCount }
      }
    }

Usage:
    from slugify import slugify
    print(slugify("Acme Corporation"))  # => "acme-corporation"
"""

import re


def slugify(name: str) -> str:
    """Convert an enterprise name into a URL-friendly slug.

    Lowercases the input, replaces runs of non-alphanumeric characters with
    a single hyphen, and strips any leading or trailing hyphens.

    Args:
        name: The enterprise name to convert.

    Returns:
        A lowercase, hyphen-separated slug suitable for use in a GitHub
        Enterprise URL (e.g. https://github.com/enterprises/<slug>).

    Examples:
        >>> slugify("Acme Corporation")
        'acme-corporation'
        >>> slugify("  My  Enterprise! ")
        'my-enterprise'
        >>> slugify("Hello_World 2024")
        'hello-world-2024'
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-")
