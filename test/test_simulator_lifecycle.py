"""
Test LuckyWorld simulator lifecycle: startup, connection, and shutdown.

This module tests the most critical path - ensuring LuckyWorld can be launched,
LuckyRobots can connect to it, and everything shuts down cleanly.
"""

import pytest
import time
import os

from luckyrobots import LuckyRobots
from luckyrobots.utils.sim_manager import (
    launch_luckyworld,
    stop_luckyworld,
    is_luckyworld_running,
)

# Test configuration from conftest.py
TEST_SCENE = "ArmLevel"
TEST_ROBOT = "so100"
TEST_TASK = "pickandplace"
SIMULATOR_CONNECTION_TIMEOUT = 240


@pytest.mark.simulator
class TestSimulatorLifecycle:
    """Test LuckyWorld simulator startup, connection, and shutdown."""

    def test_simulator_executable_found(self, simulator_executable):
        """Test that we can find a valid LuckyWorld executable"""
        assert simulator_executable is not None
        assert os.path.exists(simulator_executable)
        # Check it's an executable file
        extensions = [".exe", ".app/Contents/MacOS/LuckyWorld", ".sh"]
        assert any(simulator_executable.endswith(ext) for ext in extensions)

    def test_simulator_can_start_and_stop(self, simulator_executable):
        """Test starting and stopping the simulator independently"""
        # Ensure clean state
        if is_luckyworld_running():
            stop_luckyworld()
            time.sleep(3)

        # Test startup
        success = launch_luckyworld(
            scene=TEST_SCENE,
            robot=TEST_ROBOT,
            task=TEST_TASK,
            executable_path=simulator_executable,
            headless=True,
        )
        assert success is True
        time.sleep(60)  # Give it time to start
        assert is_luckyworld_running() is True

        # Test shutdown
        success = stop_luckyworld()
        assert success is True
        time.sleep(3)  # Give it time to stop
        assert is_luckyworld_running() is False

    def test_luckyrobots_node_startup(self, luckyworld_session):
        """Test LuckyRobots node can start and connect to simulator"""
        luckyrobots = LuckyRobots()

        try:
            # Start the node
            luckyrobots.start(
                scene=TEST_SCENE, robot=TEST_ROBOT, task=TEST_TASK, headless=True
            )

            # Test connection
            success = luckyrobots.wait_for_world_client(
                timeout=SIMULATOR_CONNECTION_TIMEOUT
            )
            assert success is True
            assert luckyrobots.world_client is not None
            assert luckyrobots._running is True

        finally:
            # Cleanup
            luckyrobots.shutdown()
            assert luckyrobots._running is False

    def test_multiple_connection_attempts(self, luckyworld_session):
        """Test that multiple LuckyRobots instances can connect sequentially"""
        instances = []

        try:
            for i in range(3):
                luckyrobots = LuckyRobots()
                luckyrobots.start(
                    scene=TEST_SCENE, robot=TEST_ROBOT, task=TEST_TASK, headless=True
                )

                success = luckyrobots.wait_for_world_client(
                    timeout=SIMULATOR_CONNECTION_TIMEOUT
                )
                assert success is True
                instances.append(luckyrobots)

                # Brief pause between connections
                time.sleep(1)

        finally:
            # Cleanup all instances
            for instance in instances:
                try:
                    instance.shutdown()
                except:
                    pass  # Ignore cleanup errors

    def test_simulator_health_check(self, luckyworld_session, simulator_health_check):
        """Test that simulator health can be verified"""
        assert simulator_health_check() is True

    def test_simulator_recovery_after_manual_restart(
        self, simulator_executable, simulator_manager
    ):
        """Test that we can recover if simulator is manually restarted"""
        # This test simulates manual intervention

        # Verify simulator is currently running
        assert simulator_manager.is_healthy()

        # Restart the simulator with same parameters
        success = simulator_manager.restart_simulator(
            scene=TEST_SCENE, robot=TEST_ROBOT, task=TEST_TASK
        )
        assert success is True

        # Verify it's running again
        assert simulator_manager.is_healthy()
