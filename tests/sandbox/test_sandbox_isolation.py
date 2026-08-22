"""Security tests for Sandbox Boundary Isolation."""

import pytest
from core.exceptions import SandboxViolationError
from sandbox.environment import SandboxEnvironment


def test_sandbox_allows_whitelisted_mock_files(sandbox_env: SandboxEnvironment) -> None:
    """Verify reading and writing within sandbox root operates normally."""
    content = sandbox_env.fs.read_file("sample_project.md")
    assert "Sample Project" in content

    # Test writing within sandbox
    sandbox_env.fs.write_file("test_out.txt", "Sandbox write test.")
    assert sandbox_env.fs.read_file("test_out.txt") == "Sandbox write test."


def test_sandbox_blocks_directory_traversal_attempts(sandbox_env: SandboxEnvironment) -> None:
    """Verify path traversal (../../) is blocked with SandboxViolationError."""
    traversal_paths = [
        "../../../../etc/passwd",
        "../../../../Users/suprith/.ssh/id_rsa",
        "../../../../Library/Keychains/login.keychain-db",
    ]

    for malicious_path in traversal_paths:
        with pytest.raises(SandboxViolationError):
            sandbox_env.fs.read_file(malicious_path)

        with pytest.raises(SandboxViolationError):
            sandbox_env.fs.write_file(malicious_path, "MALICIOUS PAYLOAD")


@pytest.mark.asyncio
async def test_mock_services_operate_on_synthetic_fixtures(sandbox_env: SandboxEnvironment) -> None:
    """Verify mock email, calendar, and messaging services return synthetic fixtures."""
    emails = await sandbox_env.email_service.list_unread_messages()
    assert len(emails) >= 1
    assert "example.com" in emails[0].sender

    events = await sandbox_env.calendar_service.list_upcoming_events()
    assert len(events) >= 1
    assert "Review" in events[0].title

    messages = await sandbox_env.messaging_service.list_recent_messages("telegram")
    assert len(messages) >= 1
    assert "@" in messages[0].sender
