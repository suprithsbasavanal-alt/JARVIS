"""Hermetic Mock Filesystem with Strict Sandbox Boundaries."""

import os
from pathlib import Path
from core.exceptions import SandboxViolationError


class MockFilesystem:
    """Provides path-scoped, hermetic filesystem access strictly within the sandbox virtual root."""

    def __init__(self, sandbox_root: Path | None = None) -> None:
        self.sandbox_root = (sandbox_root or Path("sandbox/fixtures/mock_files")).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_or_virtual_path: str) -> Path:
        """Resolve path and verify it does not escape the sandbox root."""
        # Reject explicit traversal strings early
        if ".." in relative_or_virtual_path:
            raise SandboxViolationError(
                f"Path traversal rejected: '{relative_or_virtual_path}' contains '..'"
            )

        # Strip mock file:// protocol if present
        clean_path = relative_or_virtual_path.removeprefix("file://").lstrip("/")
        target_path = (self.sandbox_root / clean_path).resolve()

        # Enforce boundary check
        try:
            target_path.relative_to(self.sandbox_root)
        except ValueError as err:
            raise SandboxViolationError(
                f"Path '{relative_or_virtual_path}' attempts to escape sandbox boundary '{self.sandbox_root}'"
            ) from err

        return target_path

    def read_file(self, path: str) -> str:
        """Read content of a sandboxed file."""
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists():
            raise FileNotFoundError(f"Mock file '{path}' does not exist.")
        with open(safe_path, encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        """Write content into a sandboxed file."""
        safe_path = self._resolve_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

    def list_files(self, directory: str = "") -> list[str]:
        """List files relative to sandbox root."""
        safe_dir = self._resolve_safe_path(directory)
        if not safe_dir.exists():
            return []
        files: list[str] = []
        for root, _, filenames in os.walk(safe_dir):
            for fn in filenames:
                rel = Path(root, fn).relative_to(self.sandbox_root)
                files.append(str(rel))
        return sorted(files)
