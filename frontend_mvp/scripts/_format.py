"""Shared formatting helpers for Taskr frontend MVP scripts.

Provides consistent, human-readable output across all shell scripts:
status icons, ANSI colors (TTY-aware), aligned columns, and friendly labels.
"""
import json
import sys


# ── ANSI colors ───────────────────────────────────────────────
class _C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


_USE_COLOR = sys.stdout.isatty()


def _c(color, text):
    """Wrap text in ANSI color if stdout is a TTY."""
    if _USE_COLOR:
        return f"{color}{text}{_C.RESET}"
    return text


# ── Status display ────────────────────────────────────────────
_STATUS = {
    "completed": ("✓", _C.GREEN, "completed"),
    "running": ("●", _C.BLUE, "running"),
    "pending": ("○", _C.GRAY, "pending"),
    "blocked": ("⏳", _C.YELLOW, "blocked"),
    "paused": ("⏸", _C.CYAN, "paused"),
    "failed": ("✗", _C.RED, "failed"),
    "cancelled": ("⊘", _C.GRAY, "cancelled"),
}

_ACTIVE_STATUSES = ("running", "blocked", "paused")
_TERMINAL_STATUSES = ("completed", "failed")


def _status_meta(status):
    return _STATUS.get(status, ("?", _C.DIM, status))


def status_icon(status):
    icon, color, _ = _status_meta(status)
    return _c(color, icon)


def status_text(status):
    """Colored 'icon status' string, e.g. '✓ completed'."""
    icon, color, label = _status_meta(status)
    return _c(color, f"{icon} {label}")


# ── Node formatting ───────────────────────────────────────────

def format_node(ns, indent=4):
    """Format a single node state as an aligned row."""
    status = ns.get("status", "unknown")
    kind = ns.get("node_kind", "?")
    title = ns.get("node_title") or ns.get("node_id", "untitled")
    icon, color, _ = _status_meta(status)

    icon_str = _c(color, icon)
    kind_str = _c(_C.DIM, kind.ljust(12))
    return f"{' ' * indent}{icon_str}  {kind_str}  {title}"


# ── Run formatting ────────────────────────────────────────────

def format_run(run, show_focus=True):
    """Format a run dict (not JSON string) into human-readable lines."""
    if isinstance(run, str):
        run = json.loads(run)

    lines = []
    rid = run.get("id", "?")
    status = run.get("status", "unknown")

    lines.append(f"  {_c(_C.BOLD, 'Run')} {_c(_C.DIM, rid)}")
    lines.append(f"  Status: {status_text(status)}")

    flow = run.get("flow_id", "")
    if flow:
        lines.append(f"  Flow:   {_c(_C.DIM, flow)}")

    reason = run.get("pause_reason")
    if reason:
        lines.append(f"  {_c(_C.YELLOW, '⏳ Waiting on')} {reason}")

    lines.append("")

    node_states = run.get("node_states", [])
    lines.append(f"  {_c(_C.BOLD, 'Steps')}")
    if not node_states:
        lines.append(f"    {_c(_C.DIM, '(none yet)')}")
    for ns in node_states:
        lines.append(format_node(ns))

    if show_focus:
        active = [ns for ns in node_states if ns.get("status") in _ACTIVE_STATUSES]
        lines.append("")
        if active:
            lines.append(f"  {_c(_C.BOLD, '▶ Active')}")
            for ns in active:
                title = ns.get("node_title") or ns.get("node_id", "?")
                lines.append(f"    {status_text(ns.get('status', '?'))}  {title}")
        else:
            if status in _TERMINAL_STATUSES:
                lines.append(f"  {_c(_C.DIM, 'Done.')}")
            else:
                lines.append(f"  {_c(_C.DIM, 'Idle — tick to advance.')}")

    return "\n".join(lines)


def format_run_row(r):
    """Compact one-line table row for list views: icon status  id  flow  created."""
    status = r.get("status", "unknown")
    rid = r.get("id", "?")
    flow = r.get("flow_id", "")
    created = (r.get("created_at") or "")[:19]
    icon, color, label = _status_meta(status)

    icon_str = _c(color, f"{icon} {label.ljust(11)}")
    rid_str = _c(_C.DIM, rid.ljust(24))
    flow_str = flow.ljust(16)
    created_str = _c(_C.DIM, created)
    return f"  {icon_str}  {rid_str}  {flow_str}  {created_str}"


# ── Flow formatting ───────────────────────────────────────────

def format_flow(f):
    """Format a flow for listing."""
    fid = f.get("id", "?")
    slug = f.get("slug", "")
    title = f.get("title", "")
    description = f.get("description", "")

    lines = [
        f"  {_c(_C.BOLD, title)}",
        f"    {_c(_C.DIM, fid)}  ·  {slug}",
    ]
    if description:
        lines.append(f"    {_c(_C.CYAN, 'asks:')} {description}")
    return "\n".join(lines)


# ── Shared UI helpers ────────────────────────────────────────

def header(title, subtitle=None):
    """A simple section header with an underline."""
    lines = [f"\n  {_c(_C.BOLD, title)}"]
    if subtitle:
        lines.append(f"  {_c(_C.DIM, subtitle)}")
    lines.append(f"  {_c(_C.DIM, '─' * max(len(title), 20))}")
    return "\n".join(lines)


def success(msg):
    return _c(_C.GREEN, f"✓ {msg}")


def failure(msg):
    return _c(_C.RED, f"✗ {msg}")


# ── Binding formatting ────────────────────────────────────────

def format_binding(b):
    """Format a binding dict (not JSON string) into human-readable lines."""
    if isinstance(b, str):
        b = json.loads(b)

    lines = []
    bid = b.get("id", "?")
    kind = b.get("kind", "?")
    title = b.get("display_title", "untitled")
    enabled = b.get("is_enabled", True)

    lines.append(f"  {_c(_C.BOLD, title)}")
    lines.append(f"    {_c(_C.DIM, bid)}  ·  {kind}  ·  {'enabled' if enabled else 'disabled'}")

    config = b.get("config")
    if config:
        lines.append(f"    {_c(_C.CYAN, 'config:')}")
        for key, value in sorted(config.items()):
            if value is None:
                continue
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            lines.append(f"      {_c(_C.DIM, key)}: {value}")
    return "\n".join(lines)


def format_binding_row(b):
    """Compact one-line table row for list views: kind  id  title."""
    bid = b.get("id", "?")
    kind = b.get("kind", "?")
    title = b.get("display_title", "")
    enabled = b.get("is_enabled", True)
    status_label = "enabled" if enabled else "disabled"
    status_color = _C.GREEN if enabled else _C.GRAY
    kind_str = _c(_C.DIM, kind.ljust(8))
    bid_str = _c(_C.DIM, bid.ljust(26))
    title_str = title.ljust(24)
    status_str = _c(status_color, status_label.ljust(10))
    return f"  {kind_str}  {bid_str}  {title_str}  {status_str}"
