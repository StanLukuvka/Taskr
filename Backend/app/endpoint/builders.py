from __future__ import annotations

from typing import Any

from app.data.repository import TaskrRepository

"""Response builder functions for Taskr API endpoints.

These helpers translate raw repository records into the public dictionary
shapes expected by the Pydantic response models. Keeping them here avoids
duplicating field-mapping logic across endpoint modules and gives a single
place to adjust the response contract.
"""


# ── Run response builders ───────────────────────────────────
