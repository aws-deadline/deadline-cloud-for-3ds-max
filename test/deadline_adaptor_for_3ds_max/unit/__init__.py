# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock

# Mock the modules that code under test uses
for module in ["pymxs"]:
    sys.modules[module] = MagicMock()
