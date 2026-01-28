"""Checked-in generated gRPC stubs for the LuckyEngine `.proto` files.

Regenerate with:
  python -m grpc_tools.protoc -I src/luckyrobots/rpc/proto \
    --python_out=src/luckyrobots/rpc/generated \
    --grpc_python_out=src/luckyrobots/rpc/generated \
    src/luckyrobots/rpc/proto/common.proto \
    src/luckyrobots/rpc/proto/media.proto \
    src/luckyrobots/rpc/proto/scene.proto \
    src/luckyrobots/rpc/proto/mujoco.proto \
    src/luckyrobots/rpc/proto/telemetry.proto \
    src/luckyrobots/rpc/proto/agent.proto \
    src/luckyrobots/rpc/proto/viewport.proto \
    src/luckyrobots/rpc/proto/camera.proto

Then adjust imports in the generated `*_pb2.py` and `*_pb2_grpc.py` to be
package-relative (`from . import ...`).
"""
