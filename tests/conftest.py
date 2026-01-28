"""
Pytest configuration and fixtures.
"""

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
        default="unitreego1",
        help="Robot name to use for tests",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires running LuckyEngine server)",
    )
