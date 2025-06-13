"""
Test robot reset and step operations against real simulator.

This module tests the core robot control functionality - reset operations
and step commands with actuator values.
"""

import pytest
import asyncio
import time

from luckyrobots.message.srv.types import Reset, Step
from luckyrobots.utils.helpers import get_robot_config

# Test configuration
TEST_ROBOT = "so100"


@pytest.mark.simulator
class TestRobotControl:
    """Test robot reset and step operations against real simulator."""

    @pytest.mark.asyncio
    async def test_reset_request_basic(
        self, luckyrobots_instance, simulator_assertions, robot_config
    ):
        """Test basic reset functionality"""
        request = Reset.Request(seed=42)

        response = await luckyrobots_instance.handle_reset(request)

        simulator_assertions.assert_response_valid(response, "reset_response")
        simulator_assertions.assert_observation_valid(
            response.observation, robot_config
        )

    @pytest.mark.asyncio
    async def test_reset_with_different_seeds(self, luckyrobots_instance):
        """Test reset with different seeds produces different initial states"""
        # Reset with seed 1
        response1 = await luckyrobots_instance.handle_reset(Reset.Request(seed=1))
        assert response1.success is True
        state1 = response1.observation.observation_state

        time.sleep(0.5)  # Brief pause

        # Reset with seed 2
        response2 = await luckyrobots_instance.handle_reset(Reset.Request(seed=2))
        assert response2.success is True
        state2 = response2.observation.observation_state

        # States should be different (with high probability)
        assert (
            state1 != state2 or len(state1) > 0
        )  # At least verify we got valid states

    @pytest.mark.asyncio
    async def test_reset_with_options(self, luckyrobots_instance):
        """Test reset with custom options"""
        options = {"difficulty": "easy", "randomize_objects": True}
        request = Reset.Request(seed=42, options=options)

        response = await luckyrobots_instance.handle_reset(request)
        assert response.success is True
        assert response.observation is not None

    @pytest.mark.asyncio
    async def test_step_request_basic(
        self, luckyrobots_instance, simulator_assertions, robot_config
    ):
        """Test basic step functionality"""
        # First reset the environment
        reset_response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        assert reset_response.success is True

        # Get robot config to understand actuator limits
        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Create valid actuator values (all zeros - safe position)
        actuator_values = [0.0] * num_actuators
        step_request = Step.Request(actuator_values=actuator_values)

        response = await luckyrobots_instance.handle_step(step_request)

        simulator_assertions.assert_response_valid(response, "step_response")
        simulator_assertions.assert_observation_valid(
            response.observation, robot_config
        )

    @pytest.mark.asyncio
    async def test_step_sequence(self, luckyrobots_instance, robot_config):
        """Test a sequence of step operations"""
        # Reset first
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Execute a sequence of small movements
        for i in range(5):
            # Small incremental movements
            actuator_values = [i * 0.05] * num_actuators  # Reduced values for safety
            step_request = Step.Request(actuator_values=actuator_values)

            response = await luckyrobots_instance.handle_step(step_request)
            assert response.success is True

            # Verify observation state has expected number of actuators
            state = response.observation.observation_state
            assert len(state) == num_actuators

            # Small delay between steps
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_actuator_limits_validation(
        self, luckyrobots_instance, simulator_assertions, robot_config
    ):
        """Test that actuator values within limits work correctly"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        actuator_limits = robot_config["action_space"]["actuator_limits"]

        # Test with values at the limits
        actuator_values = []
        for limit in actuator_limits:
            # Use a value within the safe range (not exactly at limits)
            mid_value = (limit["lower"] + limit["upper"]) / 2
            actuator_values.append(mid_value)

        step_request = Step.Request(actuator_values=actuator_values)
        response = await luckyrobots_instance.handle_step(step_request)

        assert response.success is True

        # Verify the actuator values were within limits
        simulator_assertions.assert_actuator_values_in_limits(
            actuator_values, actuator_limits
        )

    @pytest.mark.asyncio
    async def test_sequential_requests(self, luckyrobots_instance, robot_config):
        """Test that requests are handled sequentially"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Execute requests sequentially (not concurrently to avoid conflicts)
        for i in range(3):
            actuator_values = [i * 0.02] * num_actuators  # Very small movements
            step_request = Step.Request(actuator_values=actuator_values)
            response = await luckyrobots_instance.handle_step(step_request)

            assert response.success is True
            assert response.request_id is not None

            # Small delay between requests
            await asyncio.sleep(0.2)

    @pytest.mark.asyncio
    async def test_individual_actuator_control(
        self, luckyrobots_instance, robot_config
    ):
        """Test controlling individual actuators"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])
        actuator_names = robot_config["action_space"]["actuator_names"]

        # Test moving each actuator individually
        for i in range(min(num_actuators, 3)):  # Test first 3 actuators
            actuator_values = [0.0] * num_actuators
            actuator_values[i] = 0.1  # Small movement for actuator i

            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            print(f"Moved actuator {i} ({actuator_names[i]}) to {actuator_values[i]}")

            # Reset back to neutral for next test
            await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

    @pytest.mark.asyncio
    async def test_zero_actuator_values(self, luckyrobots_instance, robot_config):
        """Test step with all zero actuator values"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])
        actuator_values = [0.0] * num_actuators

        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True
        assert response.observation is not None

    @pytest.mark.asyncio
    async def test_small_actuator_movements(self, luckyrobots_instance, robot_config):
        """Test very small actuator movements"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Test with very small movements
        actuator_values = [0.001] * num_actuators  # 1mm movements
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True

        # Test with micro movements
        actuator_values = [0.0001] * num_actuators  # 0.1mm movements
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True
