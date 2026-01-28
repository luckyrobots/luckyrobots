Examples
========

Minimal gRPC Control
--------------------

LuckyRobots is gRPC-only. The most direct way to control a robot is to use
`LuckyEngineClient` to call the unified observation RPC + control RPCs.

.. code-block:: python

    import numpy as np
    from luckyrobots import LuckyEngineClient

    client = LuckyEngineClient(host="127.0.0.1", port=50051)
    client.connect()

    # Send controls (actuator targets depend on the robot you spawned)
    client.send_control(controls=[0.1, 0.2, -0.1], robot_name="two_pandas")

    # Read back a unified observation snapshot (AgentService.GetObservation)
    obs = client.get_observation(robot_name="two_pandas")
    qpos = np.array(list(obs.joint_state.positions))
    print("qpos:", qpos)

Using Robot Configuration
-------------------------

Access robot-specific settings for proper action limits:

.. code-block:: python

    import numpy as np
    from luckyrobots import LuckyRobots

    cfg = LuckyRobots.get_robot_config("two_pandas")
    limits = cfg["action_space"]["actuator_limits"]
    lower = np.array([a["lower"] for a in limits], dtype=np.float32)
    upper = np.array([a["upper"] for a in limits], dtype=np.float32)
    action = np.random.uniform(lower, upper)

Accessing Observations
----------------------

.. code-block:: python

    from luckyrobots import LuckyEngineClient

    client = LuckyEngineClient()
    client.connect()
    obs = client.get_observation(robot_name="two_pandas")
    print("positions:", list(obs.joint_state.positions))
    print("velocities:", list(obs.joint_state.velocities))

Resetting Agents
----------------

Reset agents during training or control loops:

.. code-block:: python

    from luckyrobots import LuckyEngineClient

    client = LuckyEngineClient(host="127.0.0.1", port=50051)
    client.connect()

    # Reset the default agent
    resp = client.reset_agent()
    if resp.success:
        print(f"Agent reset successful: {resp.message}")

    # Reset a specific agent
    resp = client.reset_agent(agent_name="agent_0")
    if resp.success:
        print(f"Agent 'agent_0' reset successful: {resp.message}")

Command Line Usage
------------------

Run the included controller example with different options:

.. code-block:: bash

    # Basic usage (connects to running server, resets agent every 10 seconds)
    python examples/controller.py --skip-launch

    # Specify robot and scene
    python examples/controller.py --robot unitreego1 --scene velocity --task locomotion

    # Custom rate and duration
    python examples/controller.py --rate 30 --duration 60 --skip-launch

    # Custom host/port
    python examples/controller.py --host 192.168.1.100 --port 50051 --skip-launch
