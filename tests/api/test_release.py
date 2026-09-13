"""Release operations stay unavailable outside managed environments."""

from __future__ import annotations


def test_migration_endpoint_is_hidden_in_test_environment(context) -> None:
    for path in (
        "/api/v1/internal/release/migrate",
        "/api/v1/internal/release/verify-migrations",
    ):
        response = context.client.post(
            path,
            headers={"Authorization": "Bearer not-a-release-secret"},
        )
        assert response.status_code == 404
