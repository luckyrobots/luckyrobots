"""
Pytest configuration and fixtures for LuckyRobots real simulator testing.

This conftest.py provides shared fixtures and configuration for testing
against the actual LuckyWorld simulator instead of mocks.

Key fixtures provided:
- simulator_executable: Finds and validates LuckyWorld executable
- luckyworld_session: Session-scoped simulator management
- luckyrobots_instance: Fresh LuckyRobots instance per test
- robot_config: Robot configuration data
- simulator_assertions: Custom assertions for simulator testing
- performance_monitor: Performance tracking
"""

import pytest
import asyncio
import time
import sys
import os

from luckyrobots import LuckyRobots
from luckyrobots.utils.sim_manager import (
    launch_luckyworld,
    stop_luckyworld,
    is_luckyworld_running,
    find_luckyworld_executable,
)


# Test configuration constants
SIMULATOR_STARTUP_TIMEOUT = 60
SIMULATOR_CONNECTION_TIMEOUT = 30
SIMULATOR_SHUTDOWN_TIMEOUT = 10
TEST_SCENE = "ArmLevel"
TEST_ROBOT = "so100"
TEST_TASK = "pickandplace"


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line(
        "markers", "simulator: marks tests that require the simulator"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark simulator tests"""
    for item in items:
        # Mark all tests in this module as simulator tests
        item.add_marker(pytest.mark.simulator)

        # Mark stress tests as slow
        if "stress" in item.name.lower() or "rapid" in item.name.lower():
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session", autouse=True)
def event_loop_policy():
    """Set the event loop policy for the entire test session"""
    if sys.platform.startswith("win"):
        # Use ProactorEventLoop on Windows for better subprocess support
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    else:
        # Use default policy on Unix systems
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    yield loop

    # Cleanup
    try:
        # Cancel all remaining tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Give tasks a chance to complete cancellation
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

        loop.close()
    except Exception as e:
        print(f"Error during event loop cleanup: {e}")


@pytest.fixture(scope="session")
def simulator_executable():
    """Find and validate the LuckyWorld executable"""
    executable = find_luckyworld_executable()
    if not executable:
        pytest.skip(
            "LuckyWorld executable not found. Please set LUCKYWORLD_PATH or LUCKYWORLD_HOME environment variable."
        )

    if not os.path.exists(executable):
        pytest.skip(f"LuckyWorld executable not found at: {executable}")

    print(f"Using LuckyWorld executable: {executable}")
    return executable


@pytest.fixture(scope="session")
def luckyworld_session(simulator_executable):
    """Session-scoped fixture that manages LuckyWorld simulator lifecycle"""
    print("Starting LuckyWorld simulator session...")

    # Ensure no existing instance is running
    if is_luckyworld_running():
        print("Stopping existing LuckyWorld instance...")
        stop_luckyworld()
        time.sleep(SIMULATOR_SHUTDOWN_TIMEOUT)

    # Start LuckyWorld for the test session
    print(
        f"Launching LuckyWorld: Scene={TEST_SCENE}, Robot={TEST_ROBOT}, Task={TEST_TASK}"
    )
    success = launch_luckyworld(
        scene=TEST_SCENE,
        robot=TEST_ROBOT,
        task=TEST_TASK,
        executable_path=simulator_executable,
        headless=True,  # Always run headless for testing
        verbose=False,  # Suppress verbose output unless debugging
    )

    if not success:
        pytest.fail("Failed to start LuckyWorld simulator for test session")

    # Give simulator time to fully initialize
    print("Waiting for simulator to initialize...")
    time.sleep(15)  # Increased wait time for full initialization

    # Verify simulator is still running
    if not is_luckyworld_running():
        pytest.fail("LuckyWorld simulator stopped unexpectedly after startup")

    print("LuckyWorld simulator session ready")
    yield simulator_executable

    # Cleanup after all tests in the session
    print("Shutting down LuckyWorld simulator session...")
    try:
        stop_luckyworld()
        time.sleep(SIMULATOR_SHUTDOWN_TIMEOUT)
    except Exception as e:
        print(f"Error during simulator shutdown: {e}")

    print("LuckyWorld simulator session ended")


@pytest.fixture
def luckyrobots_instance(luckyworld_session, event_loop):
    """Create a fresh LuckyRobots instance for each test"""
    print("Creating LuckyRobots instance...")

    luckyrobots = None
    try:
        luckyrobots = LuckyRobots()

        # Start the LuckyRobots node
        luckyrobots.start(
            scene=TEST_SCENE, robot=TEST_ROBOT, task=TEST_TASK, headless=True
        )

        # Wait for world client connection with timeout
        print("Waiting for LuckyRobots to connect to simulator...")
        success = luckyrobots.wait_for_world_client(
            timeout=SIMULATOR_CONNECTION_TIMEOUT
        )
        if not success:
            pytest.fail("Failed to connect LuckyRobots to LuckyWorld simulator")

        print("LuckyRobots instance ready")
        yield luckyrobots

    except Exception as e:
        pytest.fail(f"Failed to create LuckyRobots instance: {e}")

    finally:
        # Cleanup after each test
        if luckyrobots is not None:
            print("Shutting down LuckyRobots instance...")
            try:
                luckyrobots.shutdown()
            except Exception as e:
                print(f"Error during LuckyRobots shutdown: {e}")


@pytest.fixture
def fresh_luckyrobots():
    """Create a completely fresh LuckyRobots instance without automatic startup"""

    def _create_luckyrobots(**kwargs):
        """Factory function to create LuckyRobots with custom parameters"""
        return LuckyRobots(**kwargs)

    return _create_luckyrobots


@pytest.fixture
def robot_config():
    """Get the robot configuration for tests"""
    from luckyrobots.utils.helpers import get_robot_config

    return get_robot_config(TEST_ROBOT)


@pytest.fixture
def all_robot_configs():
    """Get all robot configurations for tests"""
    from luckyrobots.utils.helpers import get_robot_config

    return get_robot_config()


@pytest.fixture(autouse=True)
def test_timeout():
    """Automatically apply timeout to all tests"""
    # This helps prevent tests from hanging indefinitely
    pytest.timeout = 120  # 2 minutes max per test


@pytest.fixture
def simulator_health_check(luckyworld_session):
    """Check that the simulator is healthy before running tests"""

    def _check_health():
        if not is_luckyworld_running():
            pytest.fail("LuckyWorld simulator is not running")
        return True

    return _check_health


class SimulatorManager:
    """Helper class for managing simulator state during tests"""

    def __init__(self, executable_path):
        self.executable_path = executable_path

    def restart_simulator(self, scene=TEST_SCENE, robot=TEST_ROBOT, task=TEST_TASK):
        """Restart the simulator with new parameters"""
        if is_luckyworld_running():
            stop_luckyworld()
            time.sleep(SIMULATOR_SHUTDOWN_TIMEOUT)

        success = launch_luckyworld(
            scene=scene,
            robot=robot,
            task=task,
            executable_path=self.executable_path,
            headless=True,
        )

        if success:
            time.sleep(10)  # Wait for initialization

        return success

    def is_healthy(self):
        """Check if simulator is running and healthy"""
        return is_luckyworld_running()


@pytest.fixture
def simulator_manager(simulator_executable):
    """Provide a simulator manager for advanced test scenarios"""
    return SimulatorManager(simulator_executable)


def pytest_runtest_setup(item):
    """Setup run before each test"""
    print(f"\n--- Starting test: {item.name} ---")


def pytest_runtest_teardown(item, nextitem):
    """Teardown run after each test"""
    print(f"--- Finished test: {item.name} ---")

    # Add a small delay between tests to ensure cleanup
    time.sleep(1)


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown():
    """Session-level setup and teardown"""
    print("\n" + "=" * 60)
    print("STARTING LUCKYROBOTS INTEGRATION TEST SESSION")
    print("=" * 60)

    # Verify test environment
    try:
        import luckyrobots

        print(f"LuckyRobots version: {getattr(luckyrobots, '__version__', 'unknown')}")
    except ImportError as e:
        pytest.fail(f"Cannot import luckyrobots: {e}")

    yield

    print("\n" + "=" * 60)
    print("LUCKYROBOTS INTEGRATION TEST SESSION COMPLETE")
    print("=" * 60)


# Error handling fixtures
@pytest.fixture
def capture_simulator_logs():
    """Capture simulator output for debugging failed tests"""
    logs = []

    def _capture_log(message):
        logs.append(f"{time.time()}: {message}")

    yield _capture_log

    # If test failed, print captured logs
    if hasattr(pytest, "current_item") and pytest.current_item.failed:
        print("\n--- Captured Simulator Logs ---")
        for log in logs:
            print(log)


# Performance monitoring fixtures
@pytest.fixture
def performance_monitor():
    """Monitor test performance and simulator responsiveness"""
    start_time = time.perf_counter()

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = start_time
            self.checkpoints = []

        def checkpoint(self, name):
            current_time = time.perf_counter()
            elapsed = current_time - self.start_time
            self.checkpoints.append((name, elapsed))
            print(f"Performance checkpoint '{name}': {elapsed:.3f}s")

        def get_total_time(self):
            return time.perf_counter() - self.start_time

    monitor = PerformanceMonitor()
    yield monitor

    total_time = monitor.get_total_time()
    print(f"Total test time: {total_time:.3f}s")

    # Warn if test took too long
    if total_time > 30:  # 30 seconds
        print(f"WARNING: Test took {total_time:.1f}s - consider optimization")


# Custom assertions for simulator testing
class SimulatorAssertions:
    """Custom assertions for simulator-specific testing"""

    @staticmethod
    def assert_observation_valid(observation, robot_config):
        """Assert that an observation is valid for the given robot"""
        assert observation is not None
        assert observation.observation_state is not None

        expected_actuators = len(robot_config["observation_space"]["actuator_names"])
        assert len(observation.observation_state) == expected_actuators

        # Check that all values are finite
        for key, value in observation.observation_state.items():
            assert isinstance(value, (int, float))
            assert not (value != value)  # Check for NaN
            assert abs(value) < float("inf")  # Check for infinity

    @staticmethod
    def assert_response_valid(response, expected_type):
        """Assert that a service response is valid"""
        assert response is not None
        assert response.success is True
        assert response.request_type == expected_type
        assert response.request_id is not None
        assert response.observation is not None

    @staticmethod
    def assert_actuator_values_in_limits(values, limits):
        """Assert that actuator values are within specified limits"""
        assert len(values) == len(limits)

        for i, (value, limit) in enumerate(zip(values, limits)):
            assert (
                limit["lower"] <= value <= limit["upper"]
            ), f"Actuator {i} value {value} outside limits [{limit['lower']}, {limit['upper']}]"


@pytest.fixture
def simulator_assertions():
    """Provide custom simulator assertions"""
    return SimulatorAssertions()
