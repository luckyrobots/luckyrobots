"""
Tests for LuckyEngineClient.

Note: Tests marked with @pytest.mark.integration require a running LuckyEngine server.
Run with: pytest -m integration
"""

import pytest
from unittest.mock import MagicMock, patch

from luckyrobots import LuckyEngineClient, BenchmarkResult, ObservationResponse


class TestLuckyEngineClientUnit:
    """Unit tests that don't require a server connection."""

    def test_client_initialization(self):
        """Test client can be created with default parameters."""
        client = LuckyEngineClient(robot_name="test_robot")

        assert client.host == "127.0.0.1"
        assert client.port == 50051
        assert client.robot_name == "test_robot"
        assert not client.is_connected()

    def test_client_custom_host_port(self):
        """Test client accepts custom host and port."""
        client = LuckyEngineClient(
            host="192.168.1.100",
            port=50052,
            robot_name="test_robot",
        )

        assert client.host == "192.168.1.100"
        assert client.port == 50052

    def test_schema_cache_initialized(self):
        """Test schema cache is initialized empty."""
        client = LuckyEngineClient(robot_name="test_robot")
        assert client._schema_cache == {}

    def test_set_robot_name(self):
        """Test robot name can be changed after initialization."""
        client = LuckyEngineClient(robot_name="robot1")
        assert client.robot_name == "robot1"

        client.set_robot_name("robot2")
        assert client.robot_name == "robot2"

    def test_benchmark_invalid_method(self):
        """Test benchmark raises error for invalid method."""
        client = LuckyEngineClient(robot_name="test_robot")

        with pytest.raises(ValueError, match="Unknown method"):
            client.benchmark(method="invalid_method")


class TestObservationResponse:
    """Tests for ObservationResponse model."""

    def test_observation_response_creation(self):
        """Test ObservationResponse can be created."""
        obs = ObservationResponse(
            observation=[1.0, 2.0, 3.0],
            actions=[0.5, 0.5],
            timestamp_ms=12345,
            frame_number=100,
            agent_name="agent_0",
        )

        assert obs.observation == [1.0, 2.0, 3.0]
        assert obs.actions == [0.5, 0.5]
        assert obs.timestamp_ms == 12345
        assert obs.frame_number == 100
        assert obs.agent_name == "agent_0"

    def test_observation_response_named_access(self):
        """Test named access to observations."""
        obs = ObservationResponse(
            observation=[0.1, 0.2, 0.3],
            actions=[0.5],
            timestamp_ms=0,
            frame_number=0,
            agent_name="agent_0",
            observation_names=["x", "y", "z"],
        )

        assert obs["x"] == 0.1
        assert obs["y"] == 0.2
        assert obs["z"] == 0.3

    def test_observation_response_get_with_default(self):
        """Test get() method with default value."""
        obs = ObservationResponse(
            observation=[1.0],
            actions=[],
            timestamp_ms=0,
            frame_number=0,
            agent_name="agent_0",
            observation_names=["x"],
        )

        assert obs.get("x") == 1.0
        assert obs.get("missing", -1.0) == -1.0

    def test_observation_response_to_dict(self):
        """Test to_dict() conversion."""
        obs = ObservationResponse(
            observation=[1.0, 2.0],
            actions=[],
            timestamp_ms=0,
            frame_number=0,
            agent_name="agent_0",
            observation_names=["a", "b"],
        )

        assert obs.to_dict() == {"a": 1.0, "b": 2.0}

    def test_observation_response_to_dict_without_names(self):
        """Test to_dict() without observation names uses indices."""
        obs = ObservationResponse(
            observation=[1.0, 2.0],
            actions=[],
            timestamp_ms=0,
            frame_number=0,
            agent_name="agent_0",
        )

        assert obs.to_dict() == {"obs_0": 1.0, "obs_1": 2.0}

    def test_observation_response_named_access_without_names_raises(self):
        """Test named access raises KeyError if no names set."""
        obs = ObservationResponse(
            observation=[1.0],
            actions=[],
            timestamp_ms=0,
            frame_number=0,
            agent_name="agent_0",
        )

        with pytest.raises(KeyError, match="No observation names available"):
            _ = obs["x"]

    def test_actions_to_dict(self):
        """Test actions_to_dict() conversion."""
        obs = ObservationResponse(
            observation=[],
            actions=[0.5, 0.6],
            timestamp_ms=0,
            frame_number=0,
            agent_name="agent_0",
            action_names=["motor_0", "motor_1"],
        )

        assert obs.actions_to_dict() == {"motor_0": 0.5, "motor_1": 0.6}


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_benchmark_result_creation(self):
        """Test BenchmarkResult can be created."""
        result = BenchmarkResult(
            method="get_observation",
            duration_seconds=5.0,
            frame_count=150,
            actual_fps=30.0,
            avg_latency_ms=33.3,
            min_latency_ms=28.0,
            max_latency_ms=45.0,
            std_latency_ms=3.5,
            p50_latency_ms=32.0,
            p99_latency_ms=44.0,
        )

        assert result.method == "get_observation"
        assert result.actual_fps == 30.0
        assert result.frame_count == 150


# Minimum FPS target for integration benchmarks.
# Note: 30 FPS is the recommended control loop rate. Higher rates may work but
# are not guaranteed depending on network conditions and simulation complexity.
MIN_FPS_TARGET = 30


# Integration tests - require running LuckyEngine server
@pytest.mark.integration
class TestLuckyEngineClientIntegration:
    """Integration tests that require a running LuckyEngine server.

    Run with: pytest -m integration --host <host> --port <port> --robot <robot>
    """

    @pytest.fixture
    def client(self, request):
        """Create a connected client."""
        host = request.config.getoption("--host", default="127.0.0.1")
        port = request.config.getoption("--port", default=50051)
        robot = request.config.getoption("--robot", default="unitreego1")

        client = LuckyEngineClient(host=host, port=int(port), robot_name=robot)
        if not client.wait_for_server(timeout=10.0):
            pytest.skip("LuckyEngine server not available")
        return client

    def test_health_check(self, client):
        """Test health check passes on connected server."""
        assert client.health_check()

    def test_get_mujoco_info(self, client):
        """Test fetching MuJoCo info."""
        info = client.get_mujoco_info()
        assert hasattr(info, "nq")
        assert hasattr(info, "nv")

    def test_get_observation(self, client):
        """Test fetching observation."""
        obs = client.get_observation()
        assert isinstance(obs, ObservationResponse)
        assert isinstance(obs.observation, list)

    def test_get_joint_state(self, client):
        """Test fetching joint state."""
        resp = client.get_joint_state()
        assert hasattr(resp, "state")
        assert hasattr(resp.state, "positions")
        assert hasattr(resp.state, "velocities")

    def test_benchmark_get_observation(self, client):
        """Benchmark get_observation() performance."""
        result = client.benchmark(
            duration_seconds=3.0,
            method="get_observation",
            print_results=True,
        )

        assert result.frame_count > 0

        status = "PASS" if result.actual_fps >= MIN_FPS_TARGET else "FAIL"
        print(f"\n[{status}] get_observation: {result.actual_fps:.1f} FPS (target: {MIN_FPS_TARGET})")
        print("       Note: This measures polling speed, not simulation rate.")
        print("       May return the same observation multiple times between sim steps.")

        assert result.actual_fps >= MIN_FPS_TARGET, (
            f"get_observation FPS ({result.actual_fps:.1f}) below target ({MIN_FPS_TARGET})"
        )

    def test_benchmark_stream_agent(self, client):
        """Benchmark stream_agent() performance."""
        result = client.benchmark(
            duration_seconds=3.0,
            method="stream_agent",
            print_results=True,
        )

        assert result.frame_count > 0

        status = "PASS" if result.actual_fps >= MIN_FPS_TARGET else "FAIL"
        print(f"\n[{status}] stream_agent: {result.actual_fps:.1f} FPS (target: {MIN_FPS_TARGET})")
        print("       Note: This reflects actual simulation step rate (new frames only).")
        print("       This is the meaningful rate for control loops.")

        assert result.actual_fps >= MIN_FPS_TARGET, (
            f"stream_agent FPS ({result.actual_fps:.1f}) below target ({MIN_FPS_TARGET})"
        )
