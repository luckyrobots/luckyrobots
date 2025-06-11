"""
Shared test configuration and fixtures for LuckyRobots test suite.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch
from typing import Generator

from luckyrobots import LuckyRobots
from luckyrobots.core.models import ObservationModel, CameraData
from luckyrobots.message.srv.types import Reset, Step


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_executable_path():
    """Create a mock executable path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
        f.write(b"mock executable")
        executable_path = f.name

    yield executable_path

    # Cleanup
    if os.path.exists(executable_path):
        os.unlink(executable_path)


@pytest.fixture
def sample_observation():
    """Create a sample observation for testing."""
    return ObservationModel(
        ObservationState={
            "0": 0.0,
            "1": -1.57,
            "2": 1.57,
            "3": 0.0,
            "4": 0.0,
            "5": 0.0,
        },
        ObservationCameras=[
            CameraData(
                CameraName="laptop",
                dtype="uint8",
                shape={"width": 640, "height": 480, "channel": 3},
                TimeStamp="2024-01-01T00:00:00Z",
                ImageData=b"mock_image_data",
            )
        ],
    )


@pytest.fixture
def sample_reset_response(sample_observation):
    """Create a sample reset response for testing."""
    return Reset.Response(
        success=True,
        message="Reset successful",
        request_type="reset_response",
        request_id="test_reset_123",
        time_stamp="2024-01-01T00:00:00Z",
        observation=sample_observation,
        info={"episode": "1"},
    )


@pytest.fixture
def sample_step_response(sample_observation):
    """Create a sample step response for testing."""
    return Step.Response(
        success=True,
        message="Step successful",
        request_type="step_response",
        request_id="test_step_123",
        time_stamp="2024-01-01T00:00:00Z",
        observation=sample_observation,
        info={"reward": 0.1, "done": False},
    )


@pytest.fixture
def mock_world_client_response():
    """Mock world client response data."""
    return {
        "RequestType": "reset_response",
        "RequestID": "test_123",
        "TimeStamp": "2024-01-01T00:00:00Z",
        "Observation": {
            "ObservationState": {
                "0": 0.0,
                "1": -1.57,
                "2": 1.57,
                "3": 0.0,
                "4": 0.0,
                "5": 0.0,
            },
            "ObservationCameras": [],
        },
        "Info": {"episode": "1"},
    }


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []
        self.responses = []
        self.closed = False

    async def send_text(self, message):
        """Mock send_text method."""
        self.sent_messages.append(message)

    async def send_bytes(self, message):
        """Mock send_bytes method."""
        self.sent_messages.append(message)

    def add_response(self, response):
        """Add a response to be returned."""
        self.responses.append(response)

    async def receive_bytes(self):
        """Mock receive_bytes method."""
        if self.responses:
            return self.responses.pop(0)
        # Simulate connection closed if no more responses
        raise ConnectionClosed()

    async def close(self, code=None, reason=None):
        """Mock close method."""
        self.closed = True


class ConnectionClosed(Exception):
    """Mock connection closed exception."""

    pass


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    return MockWebSocket()
