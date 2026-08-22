"""Tool Execution Policies and Safety Boundaries."""

from enum import Enum


class ToolExecutionPolicy(str, Enum):
    """Policies governing tool runtime confinement."""
    HERMETIC_SANDBOX = "HERMETIC_SANDBOX"       # Executed only on mock filesystem / data
    READ_ONLY_PROJECT = "READ_ONLY_PROJECT"     # Can read whitelisted directories on host
    GATED_WRITE = "GATED_WRITE"                 # Can modify user files with explicit approval
    SYSTEM_RESTRICTED = "SYSTEM_RESTRICTED"     # Gated host system modifications
