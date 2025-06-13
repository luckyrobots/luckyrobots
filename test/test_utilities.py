"""
Test utility functions and configuration validation.

This module tests helper functions, configuration validation,
and other utility components of the LuckyRobots system.
"""

import pytest
import os

from luckyrobots.utils.helpers import validate_params, get_robot_config
from luckyrobots.utils.sim_manager import (
    find_luckyworld_executable,
    is_luckyworld_running,
)

# Test configuration
TEST_SCENE = "ArmLevel"
TEST_ROBOT = "so100"
TEST_TASK = "pickandplace"


@pytest.mark.simulator
class TestUtilityFunctions:
    """Test utility functions and configuration validation."""

    def test_robot_config_retrieval(self):
        """Test getting robot configurations"""
        # Test getting specific robot config
        config = get_robot_config(TEST_ROBOT)
        assert isinstance(config, dict)
        assert "observation_types" in config
        assert "available_scenes" in config
        assert "available_tasks" in config
        assert "action_space" in config
        assert "observation_space" in config

        # Test getting all configs
        all_configs = get_robot_config()
        assert isinstance(all_configs, dict)
        assert TEST_ROBOT in all_configs

    def test_robot_config_structure(self, robot_config):
        """Test robot configuration structure is valid"""
        # Check required top-level keys
        required_keys = [
            "observation_types",
            "available_scenes",
            "available_tasks",
            "action_space",
            "observation_space",
        ]
        for key in required_keys:
            assert key in robot_config, f"Missing required key: {key}"

        # Check action space structure
        action_space = robot_config["action_space"]
        assert "actuator_names" in action_space
        assert "actuator_limits" in action_space
        assert isinstance(action_space["actuator_names"], list)
        assert isinstance(action_space["actuator_limits"], list)
        assert len(action_space["actuator_names"]) == len(
            action_space["actuator_limits"]
        )

        # Check actuator limits structure
        for limit in action_space["actuator_limits"]:
            assert "name" in limit
            assert "lower" in limit
            assert "upper" in limit
            assert isinstance(limit["lower"], (int, float))
            assert isinstance(limit["upper"], (int, float))
            assert limit["lower"] <= limit["upper"]

    def test_parameter_validation_valid(self):
        """Test parameter validation with valid parameters"""
        # Should not raise any exceptions
        validate_params(
            scene=TEST_SCENE,
            robot=TEST_ROBOT,
            task=TEST_TASK,
            observation_type="pixels_agent_pos",
        )

    def test_parameter_validation_invalid_scene(self):
        """Test parameter validation with invalid scene"""
        with pytest.raises(ValueError, match="Scene.*not available"):
            validate_params(
                scene="InvalidScene",
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

    def test_parameter_validation_invalid_robot(self):
        """Test parameter validation with invalid robot"""
        with pytest.raises(KeyError):  # Robot not found in config
            validate_params(
                scene=TEST_SCENE,
                robot="invalid_robot",
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

    def test_parameter_validation_invalid_task(self):
        """Test parameter validation with invalid task"""
        with pytest.raises(ValueError, match="Task.*not available"):
            validate_params(
                scene=TEST_SCENE,
                robot=TEST_ROBOT,
                task="invalid_task",
                observation_type="pixels_agent_pos",
            )

    def test_parameter_validation_invalid_observation_type(self):
        """Test parameter validation with invalid observation type"""
        with pytest.raises(ValueError, match="Observation type.*not available"):
            validate_params(
                scene=TEST_SCENE,
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="invalid_obs_type",
            )

    def test_parameter_validation_missing_required(self):
        """Test parameter validation with missing required parameters"""
        with pytest.raises(ValueError, match="Scene is required"):
            validate_params(
                scene=None,
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

        with pytest.raises(ValueError, match="Robot is required"):
            validate_params(
                scene=TEST_SCENE,
                robot=None,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

        with pytest.raises(ValueError, match="Task is required"):
            validate_params(
                scene=TEST_SCENE,
                robot=TEST_ROBOT,
                task=None,
                observation_type="pixels_agent_pos",
            )

        with pytest.raises(ValueError, match="Observation type is required"):
            validate_params(
                scene=TEST_SCENE,
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type=None,
            )

    def test_simulator_manager_functions(self, simulator_executable):
        """Test simulator manager utility functions"""
        # Test finding executable
        found_executable = find_luckyworld_executable()
        assert found_executable is not None
        assert os.path.exists(found_executable)

        # Test status checking
        # Note: simulator should be running from session fixture
        assert is_luckyworld_running() is True

    def test_robot_config_completeness(self, all_robot_configs):
        """Test that all robot configurations are complete"""
        for robot_name, config in all_robot_configs.items():
            # Each robot should have all required sections
            required_sections = [
                "observation_types",
                "available_scenes",
                "available_tasks",
                "action_space",
                "observation_space",
            ]
            for section in required_sections:
                assert section in config, f"Robot {robot_name} missing {section}"

            # Each robot should have at least one of each
            assert (
                len(config["observation_types"]) > 0
            ), f"Robot {robot_name} has no observation types"
            assert (
                len(config["available_scenes"]) > 0
            ), f"Robot {robot_name} has no available scenes"
            assert (
                len(config["available_tasks"]) > 0
            ), f"Robot {robot_name} has no available tasks"

    def test_actuator_naming_consistency(self, robot_config):
        """Test that actuator names are consistent between action and observation spaces"""
        action_names = robot_config["action_space"]["actuator_names"]
        obs_names = robot_config["observation_space"]["actuator_names"]

        # Should have the same actuators in both spaces
        assert len(action_names) == len(obs_names)
        assert action_names == obs_names

        # Should have limits for each actuator
        action_limits = robot_config["action_space"]["actuator_limits"]
        obs_limits = robot_config["observation_space"]["actuator_limits"]

        assert len(action_limits) == len(action_names)
        assert len(obs_limits) == len(obs_names)

    def test_actuator_limits_validity(self, robot_config):
        """Test that actuator limits are reasonable"""
        for space_name in ["action_space", "observation_space"]:
            limits = robot_config[space_name]["actuator_limits"]

            for limit in limits:
                # Lower should be less than upper
                assert (
                    limit["lower"] < limit["upper"]
                ), f"Invalid limits for {limit['name']}"

                # Limits should be finite
                assert abs(limit["lower"]) < float("inf")
                assert abs(limit["upper"]) < float("inf")

                # Limits shouldn't be too extreme
                range_size = limit["upper"] - limit["lower"]
                assert range_size > 0.001, f"Range too small for {limit['name']}"
                assert range_size < 1000, f"Range too large for {limit['name']}"

    def test_camera_config_structure(self, robot_config):
        """Test camera configuration structure if present"""
        if "camera_config" in robot_config:
            camera_config = robot_config["camera_config"]

            for camera_name, config in camera_config.items():
                assert isinstance(camera_name, str)
                assert "camera_index" in config
                assert "fps" in config
                assert "camera_resolution" in config

                # Check data types
                assert isinstance(config["camera_index"], int)
                assert isinstance(config["fps"], int)
                assert isinstance(config["camera_resolution"], list)
                assert len(config["camera_resolution"]) == 2

                # Check reasonable values
                assert config["camera_index"] >= 0
                assert config["fps"] > 0
                assert config["fps"] <= 120  # Reasonable max FPS
                assert all(res > 0 for res in config["camera_resolution"])

    def test_observation_types_validity(self, robot_config):
        """Test that observation types are valid"""
        obs_types = robot_config["observation_types"]

        # Should have at least one observation type
        assert len(obs_types) > 0

        # All should be strings
        for obs_type in obs_types:
            assert isinstance(obs_type, str)
            assert len(obs_type) > 0

        # Should not have duplicates
        assert len(obs_types) == len(set(obs_types))

    def test_scene_and_task_validity(self, robot_config):
        """Test that scenes and tasks are valid"""
        scenes = robot_config["available_scenes"]
        tasks = robot_config["available_tasks"]

        # Should have at least one of each
        assert len(scenes) > 0
        assert len(tasks) > 0

        # All should be strings
        for scene in scenes:
            assert isinstance(scene, str)
            assert len(scene) > 0

        for task in tasks:
            assert isinstance(task, str)
            assert len(task) > 0

        # Should not have duplicates
        assert len(scenes) == len(set(scenes))
        assert len(tasks) == len(set(tasks))


class TestConfigurationEdgeCases:
    """Test edge cases in configuration handling"""

    def test_nonexistent_robot_config(self):
        """Test behavior with non-existent robot"""
        with pytest.raises(KeyError):
            get_robot_config("nonexistent_robot")

    def test_empty_parameters(self):
        """Test behavior with empty string parameters"""
        with pytest.raises(ValueError):
            validate_params(
                scene="",
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

        with pytest.raises(ValueError):
            validate_params(
                scene=TEST_SCENE,
                robot="",
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

    def test_case_sensitivity(self):
        """Test case sensitivity in parameter validation"""
        # Should be case sensitive
        with pytest.raises(ValueError):
            validate_params(
                scene=TEST_SCENE.lower(),  # Wrong case
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )

    def test_whitespace_handling(self):
        """Test handling of whitespace in parameters"""
        # Should handle exact matches only
        with pytest.raises(ValueError):
            validate_params(
                scene=f" {TEST_SCENE} ",  # Extra whitespace
                robot=TEST_ROBOT,
                task=TEST_TASK,
                observation_type="pixels_agent_pos",
            )
