"""
Legacy LuckyRobots WebSocket manager.

The public API of this package has moved to a gRPC-based design and no longer
exposes the old LuckyRobots node/manager abstractions. This module is kept as
an empty placeholder so that older imports do not immediately crash; new code
should import from `luckyrobots.grpc` and `luckyrobots.env` instead.
"""

__all__ = []
