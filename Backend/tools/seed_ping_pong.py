from __future__ import annotations

from app.data.repository import TaskrRepository


def seed() -> None:
    conn = TaskrRepository.get_connection()
    try:
        repo = TaskrRepository(conn)
        flow = repo.load_flow_by_slug("ping-pong")
        if flow is None:
            flow = repo.create_flow(
                "Ping Pong Demo",
                "ping-pong",
                "Three-node demo: write ping, ask Hermes to write pong, ensure done.",
            )

        version = repo.create_flow_version(flow["flow_id"])

        b_write = repo.create_binding(
            "api",
            "File API Write",
            config={
                "method": "POST",
                "url_template": "http://127.0.0.1:9121/write",
                "request_mode": "json",
                "completion_mode": "response",
            },
        )

        b_hermes = repo.create_binding(
            "hermes",
            "Hermes Write Pong",
            config={
                "board": "taskr",
                "task_title_template": "{{prompt}}",
                "task_body_template": (
                    "Read the file /agent/output/ping.txt, "
                    "then write the literal string 'pong' to /agent/output/pong.txt. "
                    "Reply with the single word 'done' when finished."
                ),
                "skills": [],
            },
        )

        b_ensure = repo.create_binding(
            "api",
            "File API Ensure Done",
            config={
                "method": "POST",
                "url_template": "http://127.0.0.1:9121/ensure",
                "request_mode": "json",
                "completion_mode": "response",
            },
        )

        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            0,
            "Write Ping",
            binding_id=b_write["binding_id"],
            input_mapping={"path": "ping.txt", "content": "ping"},
            output_mapping={},
        )
        repo.create_flow_node(
            version["flow_version_id"],
            "hermes",
            1,
            "Hermes Write Pong",
            binding_id=b_hermes["binding_id"],
            input_mapping={"prompt": "$scope.prompt"},
            output_mapping={"hermes_output": "$result"},
        )
        repo.create_flow_node(
            version["flow_version_id"],
            "api",
            2,
            "Ensure Done",
            binding_id=b_ensure["binding_id"],
            input_mapping={
                "exists_path": "pong.txt",
                "expected_content": "pong",
                "write_path": "ping_2.txt",
                "write_content": "Done",
            },
            output_mapping={"status": "$result.status"},
        )

        repo.publish_flow_version(version["flow_version_id"])
        print("Seeded ping-pong flow.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
