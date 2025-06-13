"""
Test edge cases and stress scenarios.

This module tests the robustness of the system under stress conditions,
edge cases, and potential failure scenarios.
"""

import pytest
import asyncio
import time

from luckyrobots.message.srv.types import Reset, Step

# Test configuration
TEST_SCENE = "ArmLevel"
TEST_ROBOT = "so100"
TEST_TASK = "pickandplace"


@pytest.mark.simulator
@pytest.mark.slow
class TestStressAndEdgeCases:
    """Test edge cases and stress scenarios."""

    @pytest.mark.asyncio
    async def test_rapid_reset_sequence(
        self, luckyrobots_instance, performance_monitor
    ):
        """Test rapid sequence of resets"""
        performance_monitor.checkpoint("start_rapid_resets")

        for i in range(10):
            response = await luckyrobots_instance.handle_reset(Reset.Request(seed=i))
            assert response.success is True
            assert response.observation is not None

            # Small delay to prevent overwhelming the simulator
            await asyncio.sleep(0.1)

        performance_monitor.checkpoint("end_rapid_resets")

    @pytest.mark.asyncio
    async def test_rapid_step_sequence(
        self, luckyrobots_instance, robot_config, performance_monitor
    ):
        """Test rapid sequence of steps"""
        # Reset first
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        performance_monitor.checkpoint("start_rapid_steps")

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        for i in range(20):
            # Small movements to avoid violating limits
            actuator_values = [(i % 5) * 0.005] * num_actuators
            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            # Brief delay to prevent overwhelming
            await asyncio.sleep(0.05)

        performance_monitor.checkpoint("end_rapid_steps")

    @pytest.mark.asyncio
    async def test_mixed_reset_step_sequence(self, luckyrobots_instance, robot_config):
        """Test mixed sequence of resets and steps"""
        for episode in range(3):  # Reduced for faster execution
            # Reset
            reset_response = await luckyrobots_instance.handle_reset(
                Reset.Request(seed=episode)
            )
            assert reset_response.success is True

            # Take several steps
            num_actuators = len(robot_config["action_space"]["actuator_names"])

            for step in range(5):  # Reduced steps per episode
                actuator_values = [step * 0.005] * num_actuators  # Very small movements
                step_response = await luckyrobots_instance.handle_step(
                    Step.Request(actuator_values=actuator_values)
                )
                assert step_response.success is True

                await asyncio.sleep(0.1)  # Small delay between steps

    @pytest.mark.asyncio
    async def test_large_actuator_movements(self, luckyrobots_instance, robot_config):
        """Test with large but valid actuator movements"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        actuator_limits = robot_config["action_space"]["actuator_limits"]

        # Test with 80% of maximum range for safety
        for i, limit in enumerate(actuator_limits[:3]):  # Test first 3 actuators
            range_size = limit["upper"] - limit["lower"]
            safe_value = limit["lower"] + 0.8 * range_size

            # Create actuator values with one large movement
            num_actuators = len(actuator_limits)
            actuator_values = [0.0] * num_actuators
            actuator_values[i] = safe_value

            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            await asyncio.sleep(0.3)  # Allow time for movement

            # Reset back to neutral
            await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

    @pytest.mark.asyncio
    async def test_alternating_extreme_movements(
        self, luckyrobots_instance, robot_config
    ):
        """Test alternating between extreme positions"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        actuator_limits = robot_config["action_space"]["actuator_limits"]
        num_actuators = len(actuator_limits)

        # Test first actuator with alternating extremes
        limit = actuator_limits[0]

        for i in range(4):
            if i % 2 == 0:
                value = limit["lower"] * 0.8  # 80% of lower limit
            else:
                value = limit["upper"] * 0.8  # 80% of upper limit

            actuator_values = [0.0] * num_actuators
            actuator_values[0] = value

            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            await asyncio.sleep(0.5)  # Allow time for movement

    @pytest.mark.asyncio
    async def test_timeout_behavior(self, luckyrobots_instance):
        """Test behavior under potential timeout conditions"""
        # This test verifies the system handles long operations gracefully
        start_time = time.time()

        # Perform a reset and immediately follow with steps
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        # Take multiple steps quickly
        for i in range(5):
            actuator_values = [0.01] * 6  # Assuming 6 actuators for so100
            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

        elapsed_time = time.time() - start_time

        # Should complete within reasonable time (less than 10 seconds)
        assert elapsed_time < 10, f"Operations took too long: {elapsed_time:.2f}s"

    @pytest.mark.asyncio
    async def test_edge_case_actuator_values(self, luckyrobots_instance, robot_config):
        """Test edge cases with actuator values"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Test with all zeros
        actuator_values = [0.0] * num_actuators
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True

        # Test with very small values
        actuator_values = [0.001] * num_actuators
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True

        # Test with alternating small positive/negative values
        actuator_values = [0.01 if i % 2 == 0 else -0.01 for i in range(num_actuators)]
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True

    @pytest.mark.asyncio
    async def test_precision_values(self, luckyrobots_instance, robot_config):
        """Test with high precision actuator values"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Test with high precision values
        precision_values = [0.123456789] * num_actuators
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=precision_values)
        )
        assert response.success is True

        # Test with very small precision values
        tiny_values = [1e-6] * num_actuators
        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=tiny_values)
        )
        assert response.success is True

    @pytest.mark.asyncio
    async def test_repeated_identical_commands(
        self, luckyrobots_instance, robot_config
    ):
        """Test sending identical commands repeatedly"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])
        actuator_values = [0.1] * num_actuators

        # Send the same command multiple times
        for i in range(10):
            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_long_episode_simulation(self, luckyrobots_instance, robot_config):
        """Test a long episode with many steps"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Run a long episode (50 steps)
        for step in range(50):
            # Slowly varying actuator values
            actuator_values = [0.05 * (step % 10 - 5) / 5] * num_actuators
            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            # Every 10 steps, verify observation is still valid
            if step % 10 == 0:
                obs = response.observation
                assert obs is not None
                assert len(obs.observation_state) == num_actuators

            await asyncio.sleep(0.05)  # Small delay to prevent overwhelming


@pytest.mark.simulator
class TestErrorRecovery:
    """Test error recovery and resilience scenarios"""

    @pytest.mark.asyncio
    async def test_recovery_after_multiple_resets(self, luckyrobots_instance):
        """Test system recovery after multiple rapid resets"""
        # Perform many resets to stress the system
        for i in range(20):
            response = await luckyrobots_instance.handle_reset(
                Reset.Request(seed=i % 5)
            )
            assert response.success is True

            # Very brief delay
            await asyncio.sleep(0.05)

        # System should still be responsive
        final_response = await luckyrobots_instance.handle_reset(
            Reset.Request(seed=999)
        )
        assert final_response.success is True

    @pytest.mark.asyncio
    async def test_mixed_operation_stress(self, luckyrobots_instance, robot_config):
        """Test mixed operations under stress"""
        num_actuators = len(robot_config["action_space"]["actuator_names"])

        for cycle in range(5):
            # Reset
            await luckyrobots_instance.handle_reset(Reset.Request(seed=cycle))

            # Quick sequence of steps
            for step in range(3):
                actuator_values = [step * 0.01] * num_actuators
                response = await luckyrobots_instance.handle_step(
                    Step.Request(actuator_values=actuator_values)
                )
                assert response.success is True

            # Another reset
            await luckyrobots_instance.handle_reset(Reset.Request(seed=cycle + 100))

            # Brief pause
            await asyncio.sleep(0.1)


@pytest.mark.simulator
class TestBoundaryConditions:
    """Test boundary conditions and limits"""

    @pytest.mark.asyncio
    async def test_actuator_boundary_values(self, luckyrobots_instance, robot_config):
        """Test actuator values at boundaries"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        actuator_limits = robot_config["action_space"]["actuator_limits"]
        num_actuators = len(actuator_limits)

        # Test each actuator at its boundaries
        for i, limit in enumerate(actuator_limits):
            # Test near lower bound
            actuator_values = [0.0] * num_actuators
            actuator_values[i] = limit["lower"] + 0.01  # Slightly above lower bound

            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            await asyncio.sleep(0.2)

            # Test near upper bound
            actuator_values = [0.0] * num_actuators
            actuator_values[i] = limit["upper"] - 0.01  # Slightly below upper bound

            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            assert response.success is True

            await asyncio.sleep(0.2)

            # Reset to neutral
            await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

    @pytest.mark.asyncio
    async def test_simultaneous_boundary_movements(
        self, luckyrobots_instance, robot_config
    ):
        """Test multiple actuators at boundaries simultaneously"""
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        actuator_limits = robot_config["action_space"]["actuator_limits"]

        # Move all actuators to safe boundary positions
        actuator_values = []
        for limit in actuator_limits:
            # Use 70% of range from center
            center = (limit["lower"] + limit["upper"]) / 2
            range_size = limit["upper"] - limit["lower"]
            safe_value = center + 0.35 * range_size  # 70% towards upper bound
            actuator_values.append(safe_value)

        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        assert response.success is True
