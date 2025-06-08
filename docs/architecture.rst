Architecture
============

System Overview
---------------

LuckyRobots uses a distributed node architecture with WebSocket transport:

- **Manager Node**: Central message routing
- **LuckyRobots Node**: Simulation interface
- **Controller Nodes**: User-defined controllers
- **WebSocket Transport**: Inter-node communication
- **Lucky World**: Physics simulation backend

Message System
--------------

The framework provides:

- Publisher/Subscriber patterns
- Service request/response patterns
- Distributed node communication
- Automatic service discovery
