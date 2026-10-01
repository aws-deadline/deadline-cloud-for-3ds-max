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
    # IMPORTANT: Order matters! Mock all dependencies before importing any max_submitter modules

    # Mock pymxs first
    if "pymxs" not in sys.modules:
        mock_pymxs = MagicMock()
        mock_runtime = MagicMock()
        mock_pymxs.runtime = mock_runtime
        sys.modules["pymxs"] = mock_pymxs

    # Mock PySide6 for max_submitter modules
    if "PySide6" not in sys.modules:
        mock_pyside6 = MagicMock()
        sys.modules["PySide6"] = mock_pyside6
        sys.modules["PySide6.QtCore"] = MagicMock()
        sys.modules["PySide6.QtWidgets"] = MagicMock()
        sys.modules["PySide6.QtGui"] = MagicMock()

    # Mock qtmax for max_submitter modules
    if "qtmax" not in sys.modules:
        sys.modules["qtmax"] = MagicMock()

    # Mock qtpy for max_submitter modules. QtWidgets/QtGui are stubbed as their own sys.modules
    # entries (not just left to auto-vivify off the qtpy mock) so a test can patch QMessageBox on
    # the exact module object that deadline-cloud's qt_hook_confirmation reads via a lazy
    # `from qtpy.QtWidgets import QMessageBox` — see test_pre_gui_hooks, which patches
    # sys.modules["qtpy.QtWidgets"] directly. Mirrors the Maya submitter's test module stubbing.
    #
    # Each submodule is registered independently with setdefault rather than under a single
    # `if "qtpy" not in sys.modules` guard: if a real qtpy is imported first (by a dev/CI install or
    # another plugin) but its QtWidgets submodule is not, that guard would skip the stub and
    # test_pre_gui_hooks' collection-time `sys.modules["qtpy.QtWidgets"]` lookup would KeyError.
    # setdefault fills any missing entry without clobbering an already-imported real module.
    sys.modules.setdefault("qtpy", MagicMock())
    for _qtpy_submodule in ("QtCore", "QtWidgets", "QtGui"):
        sys.modules.setdefault(f"qtpy.{_qtpy_submodule}", MagicMock())

    # Mock UI modules (these have complex Qt dependencies)
    if "ui" not in sys.modules:
        sys.modules["ui"] = MagicMock()
        sys.modules["ui.scene_settings_tab"] = MagicMock()
        sys.modules["ui.submit_dialog"] = MagicMock()

    # Set up relative import aliases BEFORE importing any max_submitter modules
    # These are needed because the modules use relative imports like "from data_classes import ..."

    # First, import data_const (it has no complex dependencies)
    if "data_const" not in sys.modules:
        from deadline.max_submitter import data_const

        sys.modules["data_const"] = data_const

    # Mock submission_utils for utilities.submission_utils relative import
    if "utilities" not in sys.modules:
        # Create a module-like object for utilities
        mock_utilities_module = MagicMock()
        mock_submission_utils = MagicMock()
        mock_utilities_module.submission_utils = mock_submission_utils
        sys.modules["utilities"] = mock_utilities_module
        sys.modules["utilities.submission_utils"] = mock_submission_utils

        # job_template_utils has no heavy dependencies (only pathlib/yaml), so
        # register the real module. This lets modules that import it via
        # "from utilities.job_template_utils import ..." resolve the real
        # functions under the mocked "utilities" package.
        from deadline.max_submitter.utilities import job_template_utils

        mock_utilities_module.job_template_utils = job_template_utils
        sys.modules["utilities.job_template_utils"] = job_template_utils

    # Now we can import data_classes (depends on data_const)
    if "data_classes" not in sys.modules:
        from deadline.max_submitter import data_classes

        sys.modules["data_classes"] = data_classes

    # Mock sanity_checks and create_job_bundle (they have complex dependencies)
    if "sanity_checks" not in sys.modules:
        sys.modules["sanity_checks"] = MagicMock()

    if "create_job_bundle" not in sys.modules:
        sys.modules["create_job_bundle"] = MagicMock()


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
