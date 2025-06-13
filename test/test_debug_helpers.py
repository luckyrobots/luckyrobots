"""
Debug and development helper tests.

This module contains tests that help with debugging and development.
These tests are primarily for inspection and troubleshooting.
"""

import pytest
import sys

from luckyrobots.message.srv.types import Reset, Step

# Test configuration
TEST_ROBOT = "so100"


@pytest.mark.simulator
class TestDebuggingHelpers:
    """Tests to help with debugging and development."""

    @pytest.mark.asyncio
    async def test_debug_observation_structure(
        self, luckyrobots_instance, robot_config
    ):
        """Debug test to print observation structure for inspection"""
        response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        observation = response.observation

        print(f"\n--- Debug: Observation Structure ---")
        print(f"Observation state keys: {list(observation.observation_state.keys())}")
        print(
            f"Observation state values: {list(observation.observation_state.values())}"
        )
        print(f"Number of actuators: {len(observation.observation_state)}")

        if observation.observation_cameras:
            print(f"Number of cameras: {len(observation.observation_cameras)}")
            for i, camera in enumerate(observation.observation_cameras):
                print(f"Camera {i}: {camera.camera_name}, shape: {camera.shape}")
        else:
            print("No cameras in observation")

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_robot_limits(self, robot_config):
        """Debug test to print robot actuator limits"""
        print(f"\n--- Debug: Robot Limits for {TEST_ROBOT} ---")

        actuator_limits = robot_config["action_space"]["actuator_limits"]
        for i, limit in enumerate(actuator_limits):
            print(
                f"Actuator {i} ({limit['name']}): [{limit['lower']:.3f}, {limit['upper']:.3f}]"
            )

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_response_timing(
        self, luckyrobots_instance, performance_monitor
    ):
        """Debug test to measure response times"""
        import time

        # Measure reset timing
        start_time = time.perf_counter()
        response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        reset_time = time.perf_counter() - start_time

        print(f"\n--- Debug: Response Timing ---")
        print(f"Reset response time: {reset_time:.3f}s")

        # Measure step timing
        actuator_values = [0.1] * 6  # Assuming 6 actuators

        step_times = []
        for i in range(5):
            start_time = time.perf_counter()
            response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            step_time = time.perf_counter() - start_time
            step_times.append(step_time)

        avg_step_time = sum(step_times) / len(step_times)
        print(f"Average step response time: {avg_step_time:.3f}s")
        print(f"Step time range: {min(step_times):.3f}s - {max(step_times):.3f}s")

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_state_transitions(self, luckyrobots_instance, robot_config):
        """Debug test to examine state transitions"""
        # Reset to known state
        reset_response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        initial_state = reset_response.observation.observation_state

        print(f"\n--- Debug: State Transitions ---")
        print(f"Initial state: {initial_state}")

        # Take a step and observe changes
        num_actuators = len(robot_config["action_space"]["actuator_names"])
        actuator_values = [0.1] * num_actuators

        step_response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        new_state = step_response.observation.observation_state

        print(f"New state after step: {new_state}")

        # Calculate and print differences
        print("State changes:")
        for key in initial_state:
            diff = new_state[key] - initial_state[key]
            if abs(diff) > 1e-6:
                print(
                    f"  {key}: {initial_state[key]:.6f} -> {new_state[key]:.6f} (Δ{diff:+.6f})"
                )

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_actuator_response(self, luckyrobots_instance, robot_config):
        """Debug test to examine individual actuator responses"""
        print(f"\n--- Debug: Individual Actuator Response ---")

        actuator_names = robot_config["action_space"]["actuator_names"]
        num_actuators = len(actuator_names)

        # Test each actuator individually
        for i, actuator_name in enumerate(actuator_names):
            await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
            initial_response = await luckyrobots_instance.handle_reset(
                Reset.Request(seed=42)
            )
            initial_state = initial_response.observation.observation_state

            # Move only this actuator
            actuator_values = [0.0] * num_actuators
            actuator_values[i] = 0.1

            step_response = await luckyrobots_instance.handle_step(
                Step.Request(actuator_values=actuator_values)
            )
            new_state = step_response.observation.observation_state

            print(f"\nActuator {i} ({actuator_name}):")
            print(f"  Command: {actuator_values[i]}")

            # Show state changes for this actuator
            for key in initial_state:
                diff = new_state[key] - initial_state[key]
                if abs(diff) > 1e-6:
                    print(f"  State {key}: {diff:+.6f}")

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_camera_info(self, luckyworld_session):
        """Debug test to examine camera information when available"""
        from luckyrobots import LuckyRobots

        luckyrobots = LuckyRobots()

        try:
            luckyrobots.start(
                scene="ArmLevel",
                robot=TEST_ROBOT,
                task="pickandplace",
                observation_type="pixels_agent_pos",
                headless=True,
            )

            success = luckyrobots.wait_for_world_client(timeout=30)
            if not success:
                print("Failed to connect for camera debug test")
                return

            response = await luckyrobots.handle_reset(Reset.Request(seed=42))
            observation = response.observation

            print(f"\n--- Debug: Camera Information ---")

            if observation.observation_cameras:
                print(f"Number of cameras: {len(observation.observation_cameras)}")

                for i, camera in enumerate(observation.observation_cameras):
                    print(f"\nCamera {i}:")
                    print(f"  Name: {camera.camera_name}")
                    print(f"  Data type: {camera.dtype}")
                    print(f"  Shape: {camera.shape}")
                    print(f"  Timestamp: {camera.time_stamp}")

                    if camera.image_data:
                        if isinstance(camera.image_data, bytes):
                            print(f"  Image data: {len(camera.image_data)} bytes")
                        else:
                            print(f"  Image data type: {type(camera.image_data)}")
                    else:
                        print("  No image data")
            else:
                print("No cameras in observation")

        finally:
            luckyrobots.shutdown()

        # This test always passes - it's just for debugging
        assert True

    def test_debug_environment_info(
        self, simulator_executable, robot_config, all_robot_configs
    ):
        """Debug test to print environment information"""
        print(f"\n--- Debug: Environment Information ---")
        print(f"Simulator executable: {simulator_executable}")
        print(f"Current robot: {TEST_ROBOT}")
        print(f"Available robots: {list(all_robot_configs.keys())}")

        print(f"\nRobot {TEST_ROBOT} configuration:")
        print(f"  Available scenes: {robot_config['available_scenes']}")
        print(f"  Available tasks: {robot_config['available_tasks']}")
        print(f"  Observation types: {robot_config['observation_types']}")
        print(
            f"  Number of actuators: {len(robot_config['action_space']['actuator_names'])}"
        )

        if "camera_config" in robot_config:
            print(
                f"  Camera configuration: {list(robot_config['camera_config'].keys())}"
            )

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_message_flow(self, luckyrobots_instance):
        """Debug test to trace message flow"""
        print(f"\n--- Debug: Message Flow ---")

        # Test reset message flow
        print("Sending reset request...")
        reset_response = await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
        print(f"Reset response received: success={reset_response.success}")
        print(f"Reset request_id: {reset_response.request_id}")
        print(f"Reset timestamp: {reset_response.time_stamp}")

        # Test step message flow
        print("\nSending step request...")
        actuator_values = [0.05] * 6  # Assuming 6 actuators
        step_response = await luckyrobots_instance.handle_step(
            Step.Request(actuator_values=actuator_values)
        )
        print(f"Step response received: success={step_response.success}")
        print(f"Step request_id: {step_response.request_id}")
        print(f"Step timestamp: {step_response.time_stamp}")

        # This test always passes - it's just for debugging
        assert True

    @pytest.mark.asyncio
    async def test_debug_error_conditions(self, luckyrobots_instance, robot_config):
        """Debug test to examine behavior near error conditions"""
        print(f"\n--- Debug: Error Condition Testing ---")

        # Test with actuator values at limits
        actuator_limits = robot_config["action_space"]["actuator_limits"]

        print("Testing actuator limit boundaries...")
        for i, limit in enumerate(actuator_limits[:2]):  # Test first 2 actuators
            print(f"\nActuator {i} ({limit['name']}):")
            print(f"  Limits: [{limit['lower']}, {limit['upper']}]")

            # Reset first
            await luckyrobots_instance.handle_reset(Reset.Request(seed=42))

            # Test near lower limit
            num_actuators = len(actuator_limits)
            actuator_values = [0.0] * num_actuators
            test_value = limit["lower"] + 0.05  # Slightly above lower limit
            actuator_values[i] = test_value

            try:
                response = await luckyrobots_instance.handle_step(
                    Step.Request(actuator_values=actuator_values)
                )
                print(f"  Near lower limit ({test_value:.3f}): SUCCESS")
            except Exception as e:
                print(f"  Near lower limit ({test_value:.3f}): ERROR - {e}")

            # Test near upper limit
            await luckyrobots_instance.handle_reset(Reset.Request(seed=42))
            actuator_values = [0.0] * num_actuators
            test_value = limit["upper"] - 0.05  # Slightly below upper limit
            actuator_values[i] = test_value

            try:
                response = await luckyrobots_instance.handle_step(
                    Step.Request(actuator_values=actuator_values)
                )
                print(f"  Near upper limit ({test_value:.3f}): SUCCESS")
            except Exception as e:
                print(f"  Near upper limit ({test_value:.3f}): ERROR - {e}")

        # This test always passes - it's just for debugging
        assert True
