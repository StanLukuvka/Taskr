import os

import uvicorn


def run() -> None:
    """Run the Taskr API server from configuration."""
    port = int(os.environ.get("TASKR_PORT", "9113"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
