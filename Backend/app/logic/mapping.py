from __future__ import annotations

from collections.abc import Mapping
from typing import Any


# ── Path traversal ──────────────────────────────────────────

def _traverse(value: Any, parts: list[str]) -> Any:
    """Walk through a nested structure using dot-separated path components.

    Supports two container types:

    * ``Mapping`` instances (e.g., ``dict``): look up the next component as a key.
    * ``list`` instances: coerce the next component to an integer and index it.

    If the current value is ``None``, not a supported container, or the path
    component is invalid/out of range, traversal stops and ``None`` is returned.

    Args:
        value: The starting value to traverse.
        parts: Ordered list of path components (already split on ``.``).

    Returns:
        The value at the end of the path, or ``None`` if the path is invalid.
    """
    current = value
    for part in parts:
        if current is None:
            return None
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


# ── Path & mapping resolution ───────────────────────────────

def resolve_path(
    path: str,
    *,
    context: Mapping[str, Any] | None = None,
    item: Any = None,
    result: Any = None,
    scope: Mapping[str, Any] | None = None,
) -> Any:
    """Resolve a string path against runtime data.

    The Taskr mapping DSL uses ``$``-prefixed paths to reference dynamic values:

    * ``$item`` / ``$item.foo.bar`` -> the current item or nested values inside it.
    * ``$result`` / ``$result.foo.bar`` -> the current result or nested values.
    * ``$scope`` / ``$scope.foo.bar`` -> the current scope or nested values.
    * ``$nodes.<node_id>.foo.bar`` -> output from another node by its identifier.

    Any string that does not start with ``$`` is returned as-is (literal value).

    Args:
        path: The path or literal value to resolve.
        context: Shared runtime context (usually contains ``nodes`` and ``scope``).
        item: The current item being processed.
        result: The current result produced by the caller.
        scope: The active scope mapping. If omitted, ``context.get("scope", {})`` is used.

    Returns:
        The resolved value, or ``None`` if the path cannot be resolved.
    """
    runtime_context = context or {}
    runtime_scope = scope if scope is not None else runtime_context.get("scope", {})

    if not path.startswith("$"):
        return path

    if path == "$item":
        return item

    if path.startswith("$item."):
        return _traverse(item, path[len("$item.") :].split("."))

    if path.startswith("$result"):
        suffix = path[len("$result") :]
        if not suffix:
            return result
        if suffix.startswith("."):
            return _traverse(result, suffix[1:].split("."))
        return None

    if path.startswith("$scope"):
        suffix = path[len("$scope") :]
        if not suffix:
            return runtime_scope
        if suffix.startswith("."):
            return _traverse(runtime_scope, suffix[1:].split("."))
        return None

    if path.startswith("$nodes."):
        parts = path[len("$nodes.") :].split(".")
        if len(parts) < 2:
            return None
        node_id, *remainder = parts
        node_data = runtime_context.get("nodes", {}).get(node_id)
        if not isinstance(node_data, Mapping):
            return None
        return _traverse(node_data, remainder)

    return None


def resolve_mapping(
    mapping: Mapping[str, Any],
    *,
    context: Mapping[str, Any] | None = None,
    item: Any = None,
    result: Any = None,
    scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Recursively resolve all string values in a flat or nested mapping.

    Each value in the input mapping is processed according to its type:

    * ``str``: passed through :func:`resolve_path`.
    * ``Mapping``: recursively resolved.
    * ``list``: each string entry is resolved; other entries are kept unchanged.
    * anything else: kept unchanged.

    Args:
        mapping: The mapping whose values should be resolved.
        context: Shared runtime context for path resolution.
        item: The current item being processed.
        result: The current result produced by the caller.
        scope: The active scope mapping.

    Returns:
        A new dictionary with all supported values resolved.
    """
    resolved: dict[str, Any] = {}
    for key, value in mapping.items():
        if isinstance(value, str):
            resolved[key] = resolve_path(value, context=context, item=item, result=result, scope=scope)
        elif isinstance(value, Mapping):
            resolved[key] = resolve_mapping(value, context=context, item=item, result=result, scope=scope)
        elif isinstance(value, list):
            entries = []
            for entry in value:
                if isinstance(entry, str):
                    entries.append(resolve_path(entry, context=context, item=item, result=result, scope=scope))
                else:
                    entries.append(entry)
            resolved[key] = entries
        else:
            resolved[key] = value
    return resolved


def resolve_output_mapping(
    mapping: Mapping[str, Any],
    *,
    context: Mapping[str, Any] | None = None,
    item: Any = None,
    result: Any = None,
    scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve an output mapping using the same rules as :func:`resolve_mapping`.

    This is a thin wrapper provided so callers can be explicit about the intent
    (resolving output/result mappings) while reusing the same implementation.

    Args:
        mapping: The output mapping to resolve.
        context: Shared runtime context for path resolution.
        item: The current item being processed.
        result: The current result produced by the caller.
        scope: The active scope mapping.

    Returns:
        A new dictionary with resolved values.
    """
    return resolve_mapping(mapping, context=context, item=item, result=result, scope=scope)
