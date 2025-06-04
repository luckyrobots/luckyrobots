LuckyRobots Documentation
========================

Hyperrealistic robotics simulation framework with Python API for embodied AI training and testing.

Quick Start
-----------

Installation::

    pip install luckyrobots

Basic Usage::

    from luckyrobots import LuckyRobots, Node
    import numpy as np

    class RobotController(Node):
        async def control_loop(self):
            reset_response = await self.reset_client.call(Reset.Request())
            actuator_values = np.array([0.1, 0.2, -0.1, 0.0, 0.5, 1.0])
            step_response = await self.step_client.call(Step.Request(actuator_values=actuator_values))

    luckyrobots = LuckyRobots()
    controller = RobotController()
    luckyrobots.register_node(controller)
    luckyrobots.start(scene="kitchen", robot="so100", task="pickandplace")

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
