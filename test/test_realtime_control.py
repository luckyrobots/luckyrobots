"""
Test robot control functionality: reset and step operations.

This tests the core robot interaction - sending reset and step commands
and receiving proper responses from the simulator.
"""

import pytest
import asyncio
import json
from unittest.mock import patch

from luckyrobots import LuckyRobots
from luckyrobots.message.srv.types import Reset, Step
from luckyrobots.core.models import ObservationModel


class TestRealtimeControl:
    """Test robot reset and step operations."""

    @pytest.mark.asyncio
    async def test_reset_request_success(
        self, mock_world_client_response, mock_websocket
    ):
        """Test successful reset request."""
        luckyrobots = LuckyRobots()
        luckyrobots.world_client = mock_websocket
        luckyrobots.process_cameras = False

        # Setup mock response
        mock_websocket.add_response(json.dumps(mock_world_client_response))

        # Create mock future that resolves immediately
        mock_future = asyncio.Future()
        mock_future.set_result(mock_world_client_response)
        luckyrobots._pending_resets["test_123"] = mock_future

        # Create reset request
        request = Reset.Request(seed=42, options={"difficulty": "easy"})

        # Mock the async parts
        with patch("secrets.token_hex", return_value="test_123"), patch(
            "asyncio.wait_for", return_value=mock_world_client_response
        ):
            response = await luckyrobots.handle_reset(request)

        assert response.success is True
        assert response.request_type == "reset_response"
        assert response.request_id == "test_123"
        assert isinstance(response.observation, ObservationModel)

    @pytest.mark.asyncio
    async def test_reset_request_no_world_client(self):
        """Test reset request fails when no world client connected."""
        luckyrobots = LuckyRobots()
        luckyrobots.world_client = None

        request = Reset.Request(seed=42)

        with pytest.raises(Exception):
            await luckyrobots.handle_reset(request)

    @pytest.mark.asyncio
    async def test_step_request_success(
        self, mock_world_client_response, mock_websocket
    ):
        """Test successful step request."""
        luckyrobots = LuckyRobots()
        luckyrobots.world_client = mock_websocket
        luckyrobots.process_cameras = False

        # Modify response for step
        step_response = mock_world_client_response.copy()
        step_response["RequestType"] = "step_response"

        # Create mock future
        mock_future = asyncio.Future()
        mock_future.set_result(step_response)
        luckyrobots._pending_steps["test_123"] = mock_future

        # Create step request with actuator values
        actuator_values = [0.0, -1.57, 1.57, 0.0, 0.0, 0.5]
        request = Step.Request(actuator_values=actuator_values)

        with patch("secrets.token_hex", return_value="test_123"), patch(
            "asyncio.wait_for", return_value=step_response
        ):
            response = await luckyrobots.handle_step(request)

        assert response.success is True
        assert response.request_type == "step_response"
        assert response.request_id == "test_123"
        assert isinstance(response.observation, ObservationModel)

    @pytest.mark.asyncio
    async def test_step_request_no_world_client(self):
        """Test step request fails when no world client connected."""
        luckyrobots = LuckyRobots()
        luckyrobots.world_client = None

        actuator_values = [0.0, -1.57, 1.57, 0.0, 0.0, 0.5]
        request = Step.Request(actuator_values=actuator_values)

        with pytest.raises(Exception):
            await luckyrobots.handle_step(request)

    def test_actuator_values_validation(self):
        """Test actuator values are properly validated."""
        # Test valid actuator values
        valid_values = [0.0, -1.57, 1.57, 0.0, 0.0, 0.5]
        request = Step.Request(actuator_values=valid_values)
        assert request.actuator_values == valid_values

        # Test with different number of actuators
        different_values = [0.1, 0.2, 0.3]
        request = Step.Request(actuator_values=different_values)
        assert request.actuator_values == different_values

    def test_reset_request_parameters(self):
        """Test reset request parameter handling."""
        # Test with seed only
        request = Reset.Request(seed=123)
        assert request.seed == 123
        assert request.options is None

        # Test with options only
        options = {"difficulty": "hard", "randomize": True}
        request = Reset.Request(options=options)
        assert request.seed is None
        assert request.options == options

        # Test with both
        request = Reset.Request(seed=456, options=options)
        assert request.seed == 456
        assert request.options == options

    @pytest.mark.asyncio
    async def test_request_timeout_handling(self, mock_websocket):
        """Test handling of request timeouts."""
        luckyrobots = LuckyRobots()
        luckyrobots.world_client = mock_websocket

        request = Reset.Request(seed=42)

        with patch("secrets.token_hex", return_value="test_timeout"), patch(
            "asyncio.wait_for", side_effect=asyncio.TimeoutError
        ):
            with pytest.raises(Exception):
                await luckyrobots.handle_reset(request)

    def test_robot_config_validation(self):
        """Test robot configuration validation."""
        from luckyrobots.utils.helpers import validate_params

        # Test valid parameters
        validate_params(
            scene="ArmLevel",
            robot="so100",
            task="pickandplace",
            observation_type="pixels_agent_pos",
        )

        # Test invalid scene
        with pytest.raises(ValueError, match="Scene.*not available"):
            validate_params(
                scene="InvalidScene",
                robot="so100",
                task="pickandplace",
                observation_type="pixels_agent_pos",
            )

        # Test invalid task
        with pytest.raises(ValueError, match="Task.*not available"):
            validate_params(
                scene="ArmLevel",
                robot="so100",
                task="invalid_task",
                observation_type="pixels_agent_pos",
            )

        # Test invalid observation type
        with pytest.raises(ValueError, match="Observation type.*not available"):
            validate_params(
                scene="ArmLevel",
                robot="so100",
                task="pickandplace",
                observation_type="invalid_obs",
            )

    def test_robot_config_retrieval(self):
        """Test robot configuration retrieval."""
        from luckyrobots import LuckyRobots

        # Test getting specific robot config
        so100_config = LuckyRobots.get_robot_config("so100")

        assert "observation_types" in so100_config
        assert "available_scenes" in so100_config
        assert "available_tasks" in so100_config
        assert "action_space" in so100_config
        assert "observation_space" in so100_config

        # Test getting all robot configs
        all_configs = LuckyRobots.get_robot_config()
        assert "so100" in all_configs
        assert isinstance(all_configs, dict)
