"""Backend test for the Product Image Prompt demo flow (flow-prompt / fv-3).

Exercises the full 3-node fake flow through the runner:
  1. Move Input Files (fake API) — copies product input files to hermes input.
  2. Generate Image Prompt (fake Hermes) — returns the canned prompt string.
  3. Image API (fake API) — confirms receipt of the prompt.

Asserts the run completes, every node is terminal, and the canned prompt
propagates from the Hermes node output to the Image API node input.
"""

from __future__ import annotations

import json
import os
import sqlite3

import pytest

from app.data.repository import SCHEMA_PATH, TaskrRepository
from app.logic.integrations.fake import FakeApiCaller, FakeHermesService
from app.logic.runner import TaskrRunner


HERMES_DIR = "/agent/output/hermes input"

EXPECTED_PROMPT = (
    "Create image\n"
    "Input summary - Product data: Pepsi Max 1.5L, NZ $1.99 (was $4.49, "
    "save $2.50), 1.33/L. No sugar, maximum taste, low calories. Ingredients "
    "include carbonated water, colour 150d, sweeteners 951/950, caffeine, "
    "phenylalanine present. Made in NZ from local and imported ingredients. - "
    "Image: studio hero shot of a 1.5L Pepsi Max bottle, black cap, dark cola, "
    "label with black/blue dot-matrix pattern, Pepsi globe, \"MAX TASTE ZERO "
    "SUGAR\" above the logo, \"PEPSI\" across the globe, \"MAX\" in red below, "
    "clean white background, bright commercial product lighting."
)


def _make_repo() -> TaskrRepository:
    """Create an in-memory repository with the canonical schema applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    repo = TaskrRepository(conn)
    repo.seed_data()
    return repo


@pytest.fixture
def clean_hermes_input():
    """Ensure hermes input is empty before and after the test."""
    os.makedirs(HERMES_DIR, exist_ok=True)
    for f in os.listdir(HERMES_DIR):
        path = os.path.join(HERMES_DIR, f)
        if os.path.isfile(path):
            os.remove(path)
    yield
    for f in os.listdir(HERMES_DIR):
        path = os.path.join(HERMES_DIR, f)
        if os.path.isfile(path):
            os.remove(path)


def test_product_image_prompt_flow_completes(clean_hermes_input) -> None:
    """Run the seeded Product Image Prompt flow from creation to completion."""
    repo = _make_repo()
    api = FakeApiCaller(image_delay=0)
    hermes = FakeHermesService()
    runner = TaskrRunner(repo, api, hermes)

    # Create a run targeting the product-image-prompt flow version directly.
    run = runner.create_run(flow_version_id="fv-3", context={})
    run_id = run["run_id"]

    # Tick until the run is no longer running.
    for _ in range(10):
        run = repo.load_run(run_id)
        if run["status"] != "running":
            break
        runner.tick(run_id)

    final_run = repo.load_run(run_id)
    assert final_run["status"] == "completed", f"Expected completed, got {final_run['status']}"

    # Every node state must be terminal.
    states = repo.load_node_states_for_run_with_node_info(run_id)
    assert len(states) == 3, f"Expected 3 node states, got {len(states)}"

    by_title = {s["node_title"]: s for s in states}
    for title in ("Move Input Files", "Generate Image Prompt", "Image API"):
        assert title in by_title, f"Missing node: {title}"
        assert by_title[title]["status"] == "completed", (
            f"Node {title} has non-terminal status: {by_title[title]['status']}"
        )

    # The Hermes node must have produced the exact canned prompt.
    hermes_state = by_title["Generate Image Prompt"]
    hermes_output = hermes_state["output"]
    assert hermes_output is not None, "Hermes node has no output"
    assert hermes_output["prompt"] == EXPECTED_PROMPT, (
        f"Prompt mismatch.\nExpected:\n{EXPECTED_PROMPT}\n\nGot:\n{hermes_output['prompt']}"
    )

    # The Image API node must have received the prompt as input.
    image_state = by_title["Image API"]
    image_input = image_state["input"]
    assert image_input is not None, "Image API node has no input"
    assert image_input["prompt"] == EXPECTED_PROMPT, (
        f"Image API input prompt mismatch.\nExpected:\n{EXPECTED_PROMPT}\n\nGot:\n{image_input['prompt']}"
    )
    assert image_state["output"]["success"] is True, "Image API did not return success"

    # The move node must report files were moved.
    move_state = by_title["Move Input Files"]
    assert move_state["output"]["moved"] is True, "Move node did not report moved=True"

    # prompt.json must be written to hermes input with the correct content.
    prompt_path = os.path.join(HERMES_DIR, "prompt.json")
    assert os.path.exists(prompt_path), "prompt.json was not written to hermes input"
    with open(prompt_path) as f:
        disk = json.load(f)
    assert disk["prompt"] == EXPECTED_PROMPT, "prompt.json on disk does not match expected prompt"

    # The image file must have been copied to hermes input.
    hermes_files = os.listdir(HERMES_DIR)
    assert "pepsi_image.jpg" in hermes_files, "pepsi_image.jpg was not copied to hermes input"
    assert "product info.txt" in hermes_files, "product info.txt was not copied to hermes input"
