"""Central Dependency Injection Container (SOLID - DIP)."""

from typing import Any, Dict, Type, TypeVar

T = TypeVar("T")


class Container:
    """Simple IoC Dependency Injection Container."""

    def __init__(self) -> None:
        self._services: Dict[Type[Any], Any] = {}
        self._factories: Dict[Type[Any], Any] = {}

    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """Binds an abstract contract interface to a concrete singleton instance."""
        self._services[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """Resolves concrete instance bound to abstract contract interface."""
        if interface not in self._services:
            raise KeyError(f"Service contract '{interface.__name__}' is not registered in container.")
        return self._services[interface]


# Central application IoC container instance
container = Container()
