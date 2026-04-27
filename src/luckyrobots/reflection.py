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

import weakref
from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    import grpc
    from google.protobuf.descriptor import ServiceDescriptor


# Per-channel cache for has_rpc / supported_services / supported_methods.
# WeakKeyDictionary so cached entries do not pin the channel in memory.
_FEATURE_CACHE: "weakref.WeakKeyDictionary[grpc.Channel, dict]" = (
    weakref.WeakKeyDictionary()
)


def _channel_cache(channel: "grpc.Channel") -> dict:
    """Return the per-channel cache dict, creating it on first use.

    Falls back to a fresh dict if the channel object is unhashable / can't
    hold a weak reference (rare for real grpc.Channel instances, but keeps
    this helper safe in tests and mocks)."""
    try:
        cache = _FEATURE_CACHE.get(channel)
        if cache is None:
            cache = {}
            _FEATURE_CACHE[channel] = cache
        return cache
    except TypeError:
        # Unhashable / non-weakrefable channel — degrade to a throwaway dict.
        return {}


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


def supported_services(channel: "grpc.Channel") -> set[str]:
    """Return the set of fully-qualified service names the server exposes.

    The first call per channel hits the reflection database; subsequent calls
    reuse a per-channel cache stored in a ``WeakKeyDictionary`` (so the cache
    never prevents the channel from being garbage-collected).

    Args:
        channel: A connected gRPC channel.

    Returns:
        Set of names like ``{"hazel.rpc.AgentService", ...}``.
    """
    cache = _channel_cache(channel)
    cached = cache.get("services")
    if cached is not None:
        return cached
    services = set(list_services(channel))
    cache["services"] = services
    return services


def supported_methods(channel: "grpc.Channel", service: str) -> set[str]:
    """Return the set of unqualified method names exposed by ``service``.

    Returns an empty set if the server does not advertise ``service`` (no
    exception — pair with :func:`supported_services` if you need to tell
    "service missing" apart from "service has zero methods").

    Cached per ``(channel, service)`` pair for the channel's lifetime.
    """
    cache = _channel_cache(channel)
    methods_by_service = cache.setdefault("methods", {})
    cached = methods_by_service.get(service)
    if cached is not None:
        return cached
    if service not in supported_services(channel):
        result: set[str] = set()
    else:
        try:
            descriptor = describe_service(channel, service)
        except KeyError:
            result = set()
        else:
            result = {m.name for m in descriptor.methods}
    methods_by_service[service] = result
    return result


def has_rpc(channel: "grpc.Channel", qualified_method: str) -> bool:
    """Return True if the server advertises ``qualified_method``.

    Both forms of separator are accepted::

        has_rpc(ch, "hazel.rpc.AgentService/SetPolicyDrivenJoints")
        has_rpc(ch, "hazel.rpc.AgentService.SetPolicyDrivenJoints")

    Results are cached per-channel (via the same ``WeakKeyDictionary`` used
    by :func:`supported_services`), so repeated probes during session start
    are cheap.
    """
    if not qualified_method:
        return False
    # Accept both `Service/Method` (gRPC wire form) and `Service.Method`
    # (proto descriptor form). We only split on the *last* separator so
    # service names like ``hazel.rpc.AgentService`` keep their dots.
    if "/" in qualified_method:
        service, _, method = qualified_method.rpartition("/")
    else:
        service, _, method = qualified_method.rpartition(".")
    if not service or not method:
        return False
    return method in supported_methods(channel, service)


__all__ = [
    "list_services",
    "describe_service",
    "describe_all",
    "has_rpc",
    "supported_services",
    "supported_methods",
]
