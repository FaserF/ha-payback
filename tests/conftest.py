"""Fixtures for PAYBACK Deutschland tests."""

import sys
import types
import pytest
import pytest_socket

# Mock fcntl module for Windows compatibility during Home Assistant test execution
if sys.platform == "win32":
    fcntl = types.ModuleType("fcntl")
    fcntl.fcntl = lambda *args, **kwargs: 0
    fcntl.ioctl = lambda *args, **kwargs: 0
    sys.modules["fcntl"] = fcntl

# Bypass pytest-socket unconditionally for testing
pytest_socket.disable_socket = lambda *args, **kwargs: None
pytest_socket.enable_socket()


@pytest.fixture(autouse=True)
async def enable_custom_integrations(hass):
    """Enable custom integrations to be loaded in tests."""
    hass.data.pop("custom_components", None)
