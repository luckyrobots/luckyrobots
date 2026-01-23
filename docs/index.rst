LuckyRobots Documentation
========================

Hyperrealistic robotics simulation framework with Python API for embodied AI training and testing.

Quick Start
-----------

Installation::

    pip install luckyrobots

Basic Usage::

    from luckyrobots import LuckyEngineClient
    import numpy as np

    client = LuckyEngineClient(host="127.0.0.1", port=50051)
    client.connect()
    client.send_control(controls=[0.1, 0.2, -0.1], robot_name="two_pandas")
    obs = client.get_observation(robot_name="two_pandas")
    qpos = np.array(list(obs.joint_state.positions))
    print("qpos:", qpos)

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api
   examples
   architecture

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
