Architecture
============

System Overview
---------------

LuckyRobots is **gRPC-only**. The Python SDK connects directly to LuckyEngine over gRPC.

Components
----------

- **LuckyEngine**: Physics simulation backend (MuJoCo-based) exposing a gRPC server
- **Python client**: `LuckyEngineClient` / `LuckyRobots` wrapper

Communication Architecture
--------------------------

.. code-block:: text

    ┌───────────────┐          gRPC           ┌─────────────────┐
    │ Python_Client │◄──────────────────────►│   LuckyEngine    │
    │ (LuckyEngine  │     (default 50051)    │ (MuJoCo + gRPC)  │
    │  Client)      │                        └─────────────────┘
    └───────────────┘

gRPC Services
-------------

LuckyEngine exposes the following gRPC services (defined in ``hazel_rpc.proto``):

- **SceneService**: Scene inspection and entity manipulation
- **MujocoService**: Joint state queries and control commands (SendControl, GetJointState)
- **AgentService**: RL-style observation/action streaming and unified snapshots (GetObservation)
- **TelemetryService**: Telemetry data streaming
- **CameraService**: Camera frame streaming
- **ViewportService**: Viewport pixel streaming

Message System
--------------

LuckyRobots no longer includes a node / pubsub / service layer. All control and observation
flows are direct gRPC calls to LuckyEngine.

Configuration
-------------

Default ports:

- gRPC server (LuckyEngine): ``127.0.0.1:50051``

Environment variables:

- ``LUCKYENGINE_PATH``: Path to LuckyEngine executable
- ``LUCKYENGINE_HOME``: Directory containing LuckyEngine
