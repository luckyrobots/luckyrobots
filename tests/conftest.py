"""
Pytest configuration and fixtures.
"""

import os
from unittest.mock import MagicMock

import pytest


def pytest_addoption(parser):
    """Add custom command line options for integration tests."""
    parser.addoption(
        "--host",
        action="store",
        default="172.24.160.1",
        help="LuckyEngine server host",
    )
    parser.addoption(
        "--port",
        action="store",
        default="50051",
        help="LuckyEngine server port",
    )
    parser.addoption(
        "--robot",
        action="store",
        default="unitreego2",
        help="Robot name to use for tests",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires running LuckyEngine server)",
    )


# ---------------------------------------------------------------------------
# Unit-test fixtures
# ---------------------------------------------------------------------------


def _make_fake_agent_stub():
    """Build a Mock-based fake AgentServiceStub for unit tests.

    Each method is a ``MagicMock`` so tests can set ``.return_value`` /
    ``.side_effect`` per RPC and inspect ``call_args``. The default return
    values are chosen so calls don't raise out of the box (success acks,
    empty controller listings, etc.); individual tests override as needed.
    """
    try:
        from luckyrobots.grpc.generated import agent_pb2
    except Exception:  # pragma: no cover - generated stubs missing
        agent_pb2 = None

    stub = MagicMock(name="FakeAgentStub")

    if agent_pb2 is not None:
        # Acks default to success=True so happy-path RPCs don't blow up.
        ok_ack = agent_pb2.PolicyOperationAck(success=True, message="")
        stub.SetPolicyActive.return_value = ok_ack
        stub.SetPolicyDescriptor.return_value = ok_ack
        stub.SetPolicyDrivenJoints.return_value = ok_ack
        stub.SetPolicyClampObservation.return_value = ok_ack
        stub.SetPolicyPriority.return_value = ok_ack
        stub.SetPolicyCommandFloat.return_value = ok_ack
        stub.SetPolicyCommandBool.return_value = ok_ack
        stub.SetMotionGraphActive.return_value = ok_ack
        stub.SetMotionGraphInput.return_value = ok_ack
        stub.FireMotionGraphTrigger.return_value = ok_ack

        stub.GetPolicyCommandFloat.return_value = agent_pb2.PolicyCommandFloatValue(
            success=True, value=0.0
        )
        stub.GetPolicyCommandBool.return_value = agent_pb2.PolicyCommandBoolValue(
            success=True, value=False
        )
        stub.GetMotionGraphActive.return_value = (
            agent_pb2.GetMotionGraphActiveResponse(success=True, active=True)
        )
        stub.ListRobotControllers.return_value = (
            agent_pb2.ListRobotControllersResponse()
        )
        stub.ListPolicyDescriptors.return_value = (
            agent_pb2.ListPolicyDescriptorsResponse()
        )
    return stub


@pytest.fixture
def fake_agent_stub():
    """Fresh Mock-based AgentServiceStub for unit tests.

    Every RPC method is a ``MagicMock`` returning a sensible canned response
    (``success=True`` acks, empty list responses). Tests reach in to set
    ``.return_value`` / ``.side_effect`` per case and inspect ``call_args``.
    """
    return _make_fake_agent_stub()


@pytest.fixture
def fake_session(fake_agent_stub):
    """A minimal Session-shaped object whose ``engine_client.agent`` is the
    fake stub. Lets unit tests construct ``RobotController(session, ...)``
    without needing a live server."""
    session = MagicMock(name="FakeSession")
    session.engine_client = MagicMock(name="FakeEngineClient")
    session.engine_client.agent = fake_agent_stub
    # Mimic the MujocoScene stub surface as well so the same fixture works
    # for both controller and scene unit tests.
    session.engine_client.mujoco_scene = MagicMock(name="FakeMujocoSceneStub")
    return session


# ---------------------------------------------------------------------------
# Integration fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session_connected(request):
    """Yield an already-connected real :class:`Session` for integration tests.

    Honours ``LR_TEST_HOST`` (formatted ``host:port``) for environment-driven
    overrides, falling back to the ``--host``/``--port`` pytest options.
    Skips the test if the server is unreachable.
    """
    from luckyrobots import Session
    from luckyrobots.client import GrpcConnectionError

    env = os.environ.get("LR_TEST_HOST")
    if env:
        host, _, port_s = env.partition(":")
        port = int(port_s) if port_s else int(
            request.config.getoption("--port", default="50051")
        )
    else:
        host = request.config.getoption("--host", default="127.0.0.1")
        port = int(request.config.getoption("--port", default="50051"))

    robot = request.config.getoption("--robot", default="unitreego2")

    sess = Session(host=host, port=int(port))
    try:
        sess.connect(timeout_s=10.0, robot=robot)
    except (GrpcConnectionError, Exception) as e:
        pytest.skip(f"LuckyEngine server not available at {host}:{port}: {e}")

    try:
        yield sess
    finally:
        sess.close(stop_engine=False)
