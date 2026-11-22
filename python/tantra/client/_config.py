"""``tantra.jsonc`` reader: JSONC parsing and ``runtime`` block resolution.

Mirrors ``tantra-agent-llm::providers::{load_config, resolve_runtime}``: values may hold
``{env:VAR}`` and ``{file:path}`` references; ``{file:}`` is relative to the config file's
directory, expands ``~`` and is whitespace-trimmed.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "RuntimeConfigError",
    "RuntimeEndpoint",
    "load_runtime_endpoint",
    "parse_jsonc",
]


class RuntimeConfigError(ValueError):
    """An ``{env:}`` / ``{file:}`` reference in the ``runtime`` block could not be resolved.

    Mirrors ``tantra-agent-llm``'s ``ConfigError``: a broken reference is an error, never a
    silently dropped token.
    """


_CONFIG_NAME = "tantra.jsonc"
_REF = re.compile(r"\{(env|file):([^}]*)\}")


@dataclass(frozen=True)
class RuntimeEndpoint:
    """Resolved runtime location. The token never appears in ``repr``."""

    url: str | None = None
    token: str | None = field(default=None, repr=False)

    def __repr__(self) -> str:
        tok = "[REDACTED]" if self.token else None
        return f"RuntimeEndpoint(url={self.url!r}, token={tok!r})"


def _strip_comments(text: str) -> str:
    out: list[str] = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    out: list[str] = []
    in_str = False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif c == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j >= n or text[j] not in "}]":
                out.append(c)
        else:
            out.append(c)
        i += 1
    return "".join(out)


def parse_jsonc(text: str) -> Any:
    """Parse JSONC (``//`` and ``/* */`` comments, trailing commas)."""
    return json.loads(_strip_trailing_commas(_strip_comments(text)))


def _substitute(value: str, base: Path) -> str:
    def repl(m: re.Match[str]) -> str:
        kind, arg = m.group(1), m.group(2).strip()
        if kind == "env":
            env_value = os.environ.get(arg)
            if env_value is None:
                raise RuntimeConfigError(f"{{env:{arg}}} references an unset variable")
            return env_value
        p = Path(arg).expanduser()
        if not p.is_absolute():
            p = base / p
        try:
            return p.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeConfigError(
                f"{{file:{arg}}} could not be read: {exc}"
            ) from exc

    return _REF.sub(repl, value)


def _runtime_block(path: Path) -> dict[str, str]:
    try:
        doc = parse_jsonc(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    block = doc.get("runtime") if isinstance(doc, dict) else None
    if not isinstance(block, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("url", "token"):
        val = block.get(key)
        if isinstance(val, str):
            val = _substitute(val, path.parent).strip()
            if val:
                out[key] = val
    return out


def _find_project_config(start: Path) -> Path | None:
    for d in (start, *start.parents):
        cand = d / _CONFIG_NAME
        if cand.is_file():
            return cand
    return None


def load_runtime_endpoint(
    path: str | os.PathLike[str] | None = None,
) -> RuntimeEndpoint:
    """Resolve the ``runtime`` block: explicit path, else walk up from cwd, over the global file."""
    merged: dict[str, str] = {}
    global_cfg = Path.home() / ".config" / "tantra" / _CONFIG_NAME
    if global_cfg.is_file():
        merged.update(_runtime_block(global_cfg))
    project = Path(path) if path is not None else _find_project_config(Path.cwd())
    if project is not None and project.is_file():
        merged.update(_runtime_block(project))
    return RuntimeEndpoint(url=merged.get("url"), token=merged.get("token"))
