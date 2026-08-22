"""Hermetic Mock Filesystem with Strict Sandbox Boundaries & Symlink Protection."""

import os
from pathlib import Path
from core.exceptions import SandboxViolationError


class MockFilesystem:
    """Provides path-scoped, hermetic filesystem access strictly within the sandbox virtual root."""

    def __init__(self, sandbox_root: Path | None = None) -> None:
        self.sandbox_root = (sandbox_root or Path("sandbox/fixtures/mock_files")).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_or_virtual_path: str) -> Path:
        """Resolve path, canonicalize symlinks, and verify it does not escape sandbox root."""
        if not relative_or_virtual_path:
            return self.sandbox_root

        # Reject path traversal patterns
        if ".." in relative_or_virtual_path:
            raise SandboxViolationError(
                f"Path traversal rejected: '{relative_or_virtual_path}' contains '..'"
            )

        # Reject sensitive system root or home directory escape attempts
        raw_str = str(relative_or_virtual_path).strip()
        if raw_str.startswith("~") or raw_str.startswith("$HOME") or raw_str.startswith("/etc") or raw_str.startswith("/var") or raw_str.startswith("/usr"):
            raise SandboxViolationError(
                f"Absolute host path access rejected: '{relative_or_virtual_path}'"
            )

        # Strip mock file:// protocol if present
        clean_path = raw_str.removeprefix("file://").lstrip("/")

        # Construct target relative to sandbox root
        target_path = self.sandbox_root / clean_path

        # Canonicalize target to resolve any symlinks
        try:
            # If target exists or parent exists, resolve symlinks
            resolved_target = target_path.resolve()
            resolved_target.relative_to(self.sandbox_root)
        except ValueError as err:
            raise SandboxViolationError(
                f"Path '{relative_or_virtual_path}' attempts to escape sandbox boundary '{self.sandbox_root}'"
            ) from err

        # Check if any parent component is a symlink pointing outside sandbox
        curr = target_path
        while curr != self.sandbox_root and curr != curr.parent:
            if curr.is_symlink():
                resolved_link = curr.resolve()
                try:
                    resolved_link.relative_to(self.sandbox_root)
                except ValueError as err:
                    raise SandboxViolationError(
                        f"Symlink '{curr}' points outside sandbox boundary: '{resolved_link}'"
                    ) from err
            curr = curr.parent

        return resolved_target

    def read_file(self, path: str) -> str:
        """Read content of a sandboxed file."""
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists() or not safe_path.is_file():
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
                file_path = Path(root, fn)
                try:
                    rel = file_path.relative_to(self.sandbox_root)
                    files.append(str(rel))
                except ValueError:
                    continue
        return sorted(files)


# Alias for backward compatibility
MockFileSystem = MockFilesystem
