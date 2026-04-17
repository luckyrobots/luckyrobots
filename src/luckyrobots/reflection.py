"""gRPC server reflection helpers.

The LuckyEngine server advertises its services via
``grpc.reflection.v1alpha.ServerReflection`` when started with
``EnableReflection = true`` (the default). These helpers let callers discover
what the connected server actually exposes at runtime — useful when a newer
engine build ships services that predate the installed ``luckyrobots``
release, or when poking at the server from an interactive session.

Example:
    >>> from luckyrobots import LuckyEngineClient
    >>> from luckyrobots.reflection import list_services, describe_service
    >>> client = LuckyEngineClient(); client.connect(); client.wait_for_server()
    >>> list_services(client.channel)
    ['hazel.rpc.AgentService', 'hazel.rpc.CameraService', ...]
    >>> describe_service(client.channel, "hazel.rpc.AgentService").methods[0].name
    'GetAgentSchema'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    import grpc
    from google.protobuf.descriptor import ServiceDescriptor


def _reflection_db(channel: "grpc.Channel"):
    """Lazy-import the reflection descriptor database.

    Imports are performed here so ``luckyrobots.reflection`` doesn't force
    ``grpcio-reflection`` into every import of the package.
    """
    try:
        from grpc_reflection.v1alpha.proto_reflection_descriptor_database import (
            ProtoReflectionDescriptorDatabase,
        )
    except ImportError as e:  # pragma: no cover - packaging guard
        raise ImportError(
            "grpc_reflection is required for runtime service discovery. "
            "Install it with `pip install grpcio-reflection`."
        ) from e
    return ProtoReflectionDescriptorDatabase(channel)


def list_services(channel: "grpc.Channel") -> list[str]:
    """Return the fully-qualified names of every service the server advertises.

    Args:
        channel: A connected gRPC channel (e.g. ``client.channel``).

    Returns:
        List of service names such as ``"hazel.rpc.AgentService"``. The
        standard ``grpc.reflection.v1alpha.ServerReflection`` entry is
        excluded so callers see only application services.
    """
    db = _reflection_db(channel)
    names = list(db.get_services())
    return [n for n in names if not n.startswith("grpc.reflection.")]


def describe_service(
    channel: "grpc.Channel", service_name: str
) -> "ServiceDescriptor":
    """Fetch a protobuf ``ServiceDescriptor`` for ``service_name``.

    The returned descriptor exposes ``.methods``, ``.full_name``, input/output
    message types and so on — everything you need to craft a dynamic call.

    Args:
        channel: A connected gRPC channel.
        service_name: Fully-qualified service name as returned by
            :func:`list_services`.

    Raises:
        KeyError: If the server doesn't advertise ``service_name``.
    """
    from google.protobuf.descriptor_pool import DescriptorPool

    db = _reflection_db(channel)
    pool = DescriptorPool(db)
    try:
        return pool.FindServiceByName(service_name)
    except KeyError as e:
        raise KeyError(f"Service '{service_name}' not found on server") from e


def describe_all(
    channel: "grpc.Channel", *, include: Optional[Iterable[str]] = None
) -> dict[str, "ServiceDescriptor"]:
    """Return descriptors for every advertised service (or the filtered subset).

    Args:
        channel: A connected gRPC channel.
        include: Optional iterable of service names to restrict the result.

    Returns:
        Mapping from fully-qualified service name to its ``ServiceDescriptor``.
    """
    names = list_services(channel)
    if include is not None:
        wanted = set(include)
        names = [n for n in names if n in wanted]
    return {name: describe_service(channel, name) for name in names}


__all__ = ["list_services", "describe_service", "describe_all"]
