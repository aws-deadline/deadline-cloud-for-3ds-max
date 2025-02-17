# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import sys
from unittest.mock import MagicMock

mock_modules = [
    "deadline.client.ui.deadline_authentication_status",
    "pymxs",
    "PySide2",
    "PySide2.QtCore",
    "PySide2.QtGui",
    "PySide2.QtWidgets",
    "qtmax",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()
