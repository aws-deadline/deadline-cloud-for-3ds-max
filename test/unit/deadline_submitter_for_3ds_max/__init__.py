# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import sys
from unittest.mock import MagicMock

mock_modules = [
    "deadline.client.ui.deadline_authentication_status",
    "pymxs",
    "qtmax",
    "qtpy",
    "qtpy.QtCore",
    "qtpy.QtWidgets",
    "qtpy.QtGui",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()
