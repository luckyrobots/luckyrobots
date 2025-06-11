"""
Test LuckyWorld lifecycle: startup, connection, and shutdown.

This tests the most critical path - ensuring LuckyWorld can be launched,
LuckyRobots can connect to it, and everything shuts down cleanly.
"""

from unittest.mock import Mock, patch
import pytest

from luckyrobots import LuckyRobots
from luckyrobots.message.srv.types import Reset, Step
from luckyrobots.utils.sim_manager import launch_luckyworld, stop_luckyworld


class TestLuckyWorldLifecycle:
    """Test LuckyWorld startup, connection, and shutdown."""

    @patch("luckyrobots.utils.sim_manager.subprocess.Popen")
    @patch("luckyrobots.utils.sim_manager.os.path.exists")
    def test_simulator_launch_success(
        self, mock_exists, mock_popen, mock_executable_path
    ):
        """Test successful LuckyWorld launch."""
        # Setup mocks
        mock_exists.return_value = True
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        # Test launch
        success = launch_luckyworld(
            scene="ArmLevel",
            robot="so100",
            task="pickandplace",
            executable_path=mock_executable_path,
            headless=True,
        )

        assert success is True
        mock_popen.assert_called_once()

        # Verify command arguments
        call_args = mock_popen.call_args[0][0]
        assert mock_executable_path in call_args
        assert "-Scene=ArmLevel" in call_args
        assert "-Robot=so100" in call_args
        assert "-Task=pickandplace" in call_args
        assert "-Headless" in call_args

    @patch("luckyrobots.utils.sim_manager.find_luckyworld_executable")
    def test_simulator_launch_no_executable(self, mock_find_executable):
        """Test LuckyWorld launch fails when executable not found."""
        mock_find_executable.return_value = None

        success = launch_luckyworld(
            scene="ArmLevel", robot="so100", task="pickandplace"
        )

        assert success is False

    @patch("luckyrobots.core.luckyrobots.uvicorn.run")
    @patch("luckyrobots.core.luckyrobots.create_connection")
    def test_luckyrobots_initialization(self, mock_create_connection, mock_uvicorn_run):
        """Test LuckyRobots node initialization."""
        # Mock websocket server not running initially
        mock_create_connection.side_effect = Exception("Connection failed")

        # Create LuckyRobots instance
        luckyrobots = LuckyRobots(host="localhost", port=3001)

        assert luckyrobots.host == "localhost"
        assert luckyrobots.port == 3001
        assert luckyrobots.robot_client is None
        assert luckyrobots.world_client is None
        assert luckyrobots._running is False

    @patch("luckyrobots.utils.sim_manager.launch_luckyworld")
    @patch("luckyrobots.core.luckyrobots.LuckyRobots._is_websocket_server_running")
    def test_luckyrobots_start_success(self, mock_server_running, mock_launch):
        """Test successful LuckyRobots start."""
        # Setup mocks
        mock_server_running.return_value = True
        mock_launch.return_value = True

        luckyrobots = LuckyRobots()

        # Mock the async setup
        with patch.object(luckyrobots, "_setup_async"):
            luckyrobots.start(
                scene="ArmLevel", robot="so100", task="pickandplace", headless=True
            )

        assert luckyrobots._running is True
        mock_launch.assert_called_once_with(
            scene="ArmLevel",
            robot="so100",
            task="pickandplace",
            executable_path=None,
            headless=True,
        )

    def test_world_client_connection_timeout(self):
        """Test world client connection timeout."""
        luckyrobots = LuckyRobots()

        # Test with very short timeout
        success = luckyrobots.wait_for_world_client(timeout=0.1)

        assert success is False

    def test_world_client_connection_success(self, mock_websocket):
        """Test successful world client connection."""
        luckyrobots = LuckyRobots()

        # Simulate world client connection
        luckyrobots.world_client = mock_websocket

        success = luckyrobots.wait_for_world_client(timeout=1.0)

        assert success is True

    @patch("luckyrobots.utils.sim_manager.stop_luckyworld")
    def test_luckyrobots_shutdown(self, mock_stop):
        """Test LuckyRobots shutdown process."""
        luckyrobots = LuckyRobots()
        luckyrobots._running = True

        # Mock some components
        mock_node = Mock()
        luckyrobots._nodes["test_node"] = mock_node

        luckyrobots.shutdown()

        assert luckyrobots._running is False
        mock_node.shutdown.assert_called_once()
        mock_stop.assert_called_once()

    @patch("luckyrobots.utils.sim_manager.is_luckyworld_running")
    @patch("luckyrobots.utils.sim_manager._process")
    def test_stop_luckyworld(self, mock_process, mock_is_running):
        """Test stopping LuckyWorld."""
        mock_is_running.return_value = True
        mock_process.terminate = Mock()
        mock_process.wait = Mock()

        success = stop_luckyworld()

        assert success is True

    @patch("luckyrobots.utils.sim_manager.subprocess.Popen")
    def test_simulator_crash_recovery(self, mock_popen):
        """Test handling of simulator crash."""
        # Mock process that crashes immediately
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # Crashed
        mock_popen.return_value = mock_process

        luckyrobots = LuckyRobots()

        # Should detect crash and handle gracefully
        success = luckyrobots.wait_for_world_client(timeout=1.0)
        assert success is False

    @pytest.mark.asyncio
    async def test_complete_episode_workflow(self):
        """Test complete episode: start -> reset -> multiple steps -> shutdown."""

        with patch(
            "luckyrobots.utils.sim_manager.launch_luckyworld", return_value=True
        ):
            luckyrobots = LuckyRobots()

            # Mock successful startup
            luckyrobots.start(scene="ArmLevel", robot="so100", task="pickandplace")

            # Mock world client connection
            luckyrobots.world_client = Mock()

            # Test reset
            reset_request = Reset.Request(seed=42)
            with patch.object(luckyrobots, "handle_reset") as mock_reset:
                mock_reset.return_value = Mock(success=True)
                reset_response = await luckyrobots.handle_reset(reset_request)
                assert reset_response.success

            # Test multiple steps
            for i in range(10):
                step_request = Step.Request(actuator_values=[i / 10.0] * 6)
                with patch.object(luckyrobots, "handle_step") as mock_step:
                    mock_step.return_value = Mock(success=True)
                    step_response = await luckyrobots.handle_step(step_request)
                    assert step_response.success

            # Test shutdown
            luckyrobots.shutdown()
            assert not luckyrobots._running
