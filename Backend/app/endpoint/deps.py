def _get_repo() -> TaskrRepository:
    """Build a TaskrRepository with a fresh connection.

    This is a lightweight factory used by endpoints that only need data access
    and do not drive the run execution engine.
    """
    conn = TaskrRepository.get_connection()
    return TaskrRepository(conn)
