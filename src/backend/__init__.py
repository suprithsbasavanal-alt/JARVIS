"""Backend Package."""

from .container.di_container import Container, container
from .bootstrap.main import bootstrap_application

__all__ = [
    "Container",
    "container",
    "bootstrap_application",
]
