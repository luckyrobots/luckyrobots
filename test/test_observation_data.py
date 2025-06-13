"""
Test observation data processing and camera data handling.

This module tests the critical data processing pipeline - ensuring observations
and camera data are properly parsed and processed from the real simulator.
"""

import pytest
import asyncio
import numpy as np

from luckyrobots import LuckyRobots
from luckyrobots.message.srv.types import Reset, Step
from luckyrobots.core.models import CameraData

# Test configuration
TEST_SCENE = "ArmLevel"
TEST_ROBOT = "so100"
TEST_TASK = "pickandplace"
SIMULATOR_CONNECTION_TIMEOUT = 30


@pytest.mark.simulator
class TestObservationData:
    """Test observation and camera data processing with real simulator data."""

    @pytest.mark.asyncio
    async def test_observation_structure_after_reset(
        self, luckyrobots_instance, simulator_assertions, robot_config
    ):
        """Test observation data structure after reset"""
        response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        observation = response.observation

        # Test basic structure
        simulator_assertions.assert_observation_valid(observation, robot_config)

        # Verify actuator states match robot configuration
        expected_actuators = len(robot_config["observation_space"]["actuator_names"])
        assert len(observation.observation_state) == expected_actuators

        # Verify all state values are numeric and finite
        for key, value in observation.observation_state.items():
            assert isinstance(value, (int, float))
            assert not (value != value)  # Check for NaN
            assert abs(value) < float("inf")  # Check for infinity

    @pytest.mark.asyncio
    async def test_observation_structure_after_step(
        self, luckyrobots_instance, simulator_assertions, robot_config
    ):
        """Test observation data structure after step"""
        # Reset first
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        # Take a step
        num_actuators = len(robot_config["action_space"]["actuator_names"])
        actuator_values = [0.05] * num_actuators  # Small movement

        response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        observation = response.observation

        # Same structural tests as reset
        simulator_assertions.assert_observation_valid(observation, robot_config)

        # Verify state values are within expected ranges
        actuator_limits = robot_config["observation_space"]["actuator_limits"]
        state_values = list(observation.observation_state.values())

        for i, (value, limit) in enumerate(zip(state_values, actuator_limits)):
            assert (
                limit["lower"] <= value <= limit["upper"]
            ), f"Actuator {i} value {value} outside limits [{limit['lower']}, {limit['upper']}]"

    @pytest.mark.asyncio
    async def test_observation_consistency_across_resets(self, luckyrobots_instance):
        """Test that observations are consistent across resets with same seed"""
        seed = 123

        # First reset
        response1 = await luckyrobots_instance.handle_reset(Reset.Request(seed=seed))
        state1 = response1.observation.observation_state

        await asyncio.sleep(0.5)  # Brief pause

        # Second reset with same seed
        response2 = await luckyrobots_instance.handle_reset(Reset.Request(seed=seed))
        state2 = response2.observation.observation_state

        # States should be identical with same seed
        assert state1 == state2

    @pytest.mark.asyncio
    async def test_state_changes_after_actions(
        self, luckyrobots_instance, robot_config
    ):
        """Test that robot state changes after taking actions"""
        # Reset to known state
        reset_response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        initial_state = reset_response.observation.observation_state.copy()

        # Take a meaningful action
        num_actuators = len(robot_config["action_space"]["actuator_names"])

        # Move first actuator significantly
        actuator_values = [0.0] * num_actuators
        actuator_values[0] = 0.3  # Significant movement

        step_response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        final_state = step_response.observation.observation_state

        # At least one state value should have changed
        state_changed = any(
            abs(initial_state[key] - final_state[key]) > 1e-6
            for key in initial_state.keys()
        )

        # If no immediate change, take a few more steps to allow physics to settle
        if not state_changed:
            for i in range(5):
                await asyncio.sleep(0.2)
                step_response = await luckyrobots_instance.handle_step(
                    Step.Request(actuator_values=actuator_values)
                )
                final_state = step_response.observation.observation_state
                state_changed = any(
                    abs(initial_state[key] - final_state[key]) > 1e-6
                    for key in initial_state.keys()
                )
                if state_changed:
                    break

        # We should see some change eventually
        assert state_changed, "Robot state did not change after taking actions"

    @pytest.mark.asyncio
    async def test_observation_data_types(self, luckyrobots_instance, robot_config):
        """Test that observation data types are correct"""
        response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        observation = response.observation

        # Check observation state data types
        for key, value in observation.observation_state.items():
            assert isinstance(key, str), f"Observation key {key} is not a string"
            assert isinstance(
                value, (int, float)
            ), f"Observation value {value} is not numeric"

        # Check camera data types if present
        if observation.observation_cameras:
            for camera in observation.observation_cameras:
                assert isinstance(camera.camera_name, str)
                assert isinstance(camera.dtype, str)

                if camera.time_stamp:
                    assert isinstance(camera.time_stamp, str)

    @pytest.mark.asyncio
    async def test_observation_state_keys(self, luckyrobots_instance, robot_config):
        """Test that observation state keys match expected actuator names or indices"""
        response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        observation = response.observation

        state_keys = list(observation.observation_state.keys())
        expected_count = len(robot_config["observation_space"]["actuator_names"])

        # Should have the right number of state values
        assert len(state_keys) == expected_count

        # Keys should be either string indices or actuator names
        for key in state_keys:
            assert isinstance(key, str)
            # Could be numeric indices like "0", "1", "2" or actual names
            assert len(key) > 0

    @pytest.mark.asyncio
    async def test_camera_data_when_enabled(self, luckyworld_session):
        """Test camera data when cameras are enabled"""
        # Create LuckyRobots instance with camera processing enabled
        luckyrobots = LuckyRobots()

        try:
            luckyrobots.start(
                scene=TEST_SCENE,
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",  # This should enable cameras
                headless=True,
            )

            success = luckyrobots.wait_for_world_client(
                timeout=SIMULATOR_CONNECTION_TIMEOUT
            )
            assert success is True

            response = await luckyrobots.handle_reset(Reset.Request(seed=42))
            observation = response.observation

            # Check if cameras are present
            if observation.observation_cameras is not None:
                assert isinstance(observation.observation_cameras, list)
                assert len(observation.observation_cameras) > 0

                for camera in observation.observation_cameras:
                    assert isinstance(camera, CameraData)
                    assert camera.camera_name is not None
                    assert camera.dtype is not None
                    assert camera.shape is not None

                    # Verify shape structure
                    if isinstance(camera.shape, dict):
                        assert "width" in camera.shape
                        assert "height" in camera.shape
                        assert "channel" in camera.shape
                        assert camera.shape["width"] > 0
                        assert camera.shape["height"] > 0
                        assert camera.shape["channel"] > 0

                    # If image data is present, verify it's valid
                    if camera.image_data is not None:
                        if isinstance(camera.image_data, bytes):
                            assert len(camera.image_data) > 0
                        elif isinstance(camera.image_data, np.ndarray):
                            assert camera.image_data.size > 0

        finally:
            luckyrobots.shutdown()

    @pytest.mark.asyncio
    async def test_camera_data_processing(self, luckyworld_session):
        """Test camera data processing pipeline"""
        luckyrobots = LuckyRobots()

        try:
            luckyrobots.start(
                scene=TEST_SCENE,
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
                headless=True,
            )

            success = luckyrobots.wait_for_world_client(
                timeout=SIMULATOR_CONNECTION_TIMEOUT
            )
            assert success is True

            response = await luckyrobots.handle_reset(Reset.Request(seed=42))
            observation = response.observation

            if observation.observation_cameras:
                # Test processing all cameras
                observation.process_all_cameras()

                for camera in observation.observation_cameras:
                    # If camera had image data, it should now be processed
                    if camera.image_data is not None:
                        # After processing, should be numpy array or None
                        assert camera.image_data is None or isinstance(
                            camera.image_data, np.ndarray
                        )

        finally:
            luckyrobots.shutdown()

    @pytest.mark.asyncio
    async def test_observation_stability_over_time(self, luckyrobots_instance):
        """Test that observations remain stable when no actions are taken"""
        # Reset to a known state
        await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

        # Take multiple observations with no actions
        observations = []
        for i in range(3):
            # Use zero movements (no action)
            actuator_values = [0.0] * 6  # Assuming 6 actuators for so100
            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            observations.append(response.observation.observation_state)
            await asyncio.sleep(0.1)

        # States should be very similar (allowing for small physics variations)
        for i in range(1, len(observations)):
            for key in observations[0].keys():
                diff = abs(observations[0][key] - observations[i][key])
                assert diff < 0.01, f"State {key} changed too much: {diff}"

    @pytest.mark.asyncio
    async def test_observation_bounds_checking(
        self, luckyrobots_instance, robot_config
    ):
        """Test that all observation values are within reasonable bounds"""
        response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        observation = response.observation

        actuator_limits = robot_config["observation_space"]["actuator_limits"]
        state_values = list(observation.observation_state.values())

        # Check that all observation values are within the defined limits
        for i, (value, limit) in enumerate(zip(state_values, actuator_limits)):
            assert (
                limit["lower"] <= value <= limit["upper"]
            ), f"Observation actuator {i} value {value} outside limits [{limit['lower']}, {limit['upper']}]"
