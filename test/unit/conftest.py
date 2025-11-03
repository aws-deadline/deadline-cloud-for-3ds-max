# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Pytest configuration for unit tests.

This module provides fixtures for mocking pymxs which can only be imported inside 3ds Max.
"""

import sys

import pytest
from unittest.mock import MagicMock


# Mock pymxs before any imports that depend on it
# This runs during pytest configuration, before test collection
def pytest_configure(config):
    """Configure pytest with necessary mocks for 3ds Max modules."""
    if "pymxs" not in sys.modules:
        # Create a mock for pymxs
        mock_pymxs = MagicMock()
        mock_runtime = MagicMock()
        mock_pymxs.runtime = mock_runtime

        # Add to sys.modules so imports will use the mock
        sys.modules["pymxs"] = mock_pymxs


@pytest.fixture(scope="function")
def pymxs_mock():
    """
    Fixture to provide access to the mocked pymxs module.

    This fixture can be used in tests that need to interact with or verify
    calls to the pymxs mock.

    Returns:
        MagicMock: The mocked pymxs module
    """
    return sys.modules.get("pymxs")
