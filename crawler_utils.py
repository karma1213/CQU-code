#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared I/O helpers for the crawler entry points."""

import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit


_CHARSET_RE = re.compile(
    rb"charset\s*=\s*[\"']?([A-Za-z0-9._-]+)",
    re.IGNORECASE,
)


def decode_response(response):
    """Raise for HTTP errors and decode a requests response conservatively."""
    response.raise_for_status()
    content = response.content
    if content.startswith(b"\xef\xbb\xbf"):
        return content.decode("utf-8-sig")

    encodings = []
    declared = response.encoding
    if declared and declared.lower() not in {"iso-8859-1", "latin-1"}:
        encodings.append(declared)
    match = _CHARSET_RE.search(content[:4096])
    if match:
        encodings.append(match.group(1).decode("ascii", "ignore"))
    encodings.append("utf-8")
    if response.apparent_encoding:
        encodings.append(response.apparent_encoding)
    encodings.append("gb18030")

    seen = set()
    for encoding in encodings:
        normalized = encoding.lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        try:
            return content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return content.decode("utf-8", errors="replace")


def safe_http_url(value, base="", allowed_hosts=()):
    """Return a normalized HTTP(S) URL, or an empty string when unsafe."""
    candidate = urljoin(base, (value or "").strip())
    try:
        parts = urlsplit(candidate)
        hostname = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    if parts.scheme.lower() not in {"http", "https"} or not hostname:
        return ""
    if parts.username is not None or parts.password is not None:
        return ""
    if allowed_hosts and not any(
        hostname == host or hostname.endswith("." + host)
        for host in (item.lower().rstrip(".") for item in allowed_hosts)
    ):
        return ""
    return urlunsplit((parts.scheme.lower(), parts.netloc, parts.path, parts.query, parts.fragment))


def write_text_atomic(path, content):
    """Replace a UTF-8 text file atomically without exposing partial output."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
