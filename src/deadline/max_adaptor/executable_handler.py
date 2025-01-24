"""
3ds Max Deadline Cloud Adaptor - 3dsMax Executable Handler

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

from enum import Enum
from os import environ
from functools import cache
import re
from typing import List, Dict, Match, Optional
from dataclasses import dataclass


class SupportedMaxExecutable(Enum):
    INTERACTIVE = "3dsmax"
    BATCH = "3dsmaxbatch"


@dataclass
class MaxExecutable:
    full_path: str
    exe_type: SupportedMaxExecutable


class MaxExecutableHandler:
    """
    Bussiness logic layer to take to facilitate supporting multiple 3dsMax executables.
    """

    def __init__(self):
        # Execution configuration by executable type.
        self._max_exe_parameters: Dict[SupportedMaxExecutable, List[str]] = {
            SupportedMaxExecutable.INTERACTIVE: ["-silent", "-dm", "-U", "PythonHost"],
            SupportedMaxExecutable.BATCH: ["-dm", "on", "-v", "5"],
        }

    @property
    @cache
    def max_executable(self) -> MaxExecutable:
        """
        The 3dsMax executable is determined on the fly, based on the 3DSMAX_EXECUTABLE environment variable.
        If 3DSMAX_EXECUTABLE is not set, it defaults to '3dsmax'.
        :returns: Data object containing the details of the 3dsMax executable.
        :throws ValueError: If the value set in 3DSMAX_EXECUTABLE is not recognized as a valid 3dsMax executable.
        """
        max_exe_path: str = environ.get("3DSMAX_EXECUTABLE", "3dsmax")
        pattern: str = r"[\\\/]?([^\\\/]+?)(\.exe)?$"

        match: Optional[Match[str]] = re.search(pattern, max_exe_path)

        if not match:
            raise ValueError(f"Unable to get a 3dsMax executable from path {max_exe_path}")

        max_exe: Optional[str] = match.group(1)
        if any(max_exe == supported_max_exe.value for supported_max_exe in SupportedMaxExecutable):
            return MaxExecutable(full_path=max_exe_path, exe_type=SupportedMaxExecutable(max_exe))

        raise ValueError(
            f"No valid 3dsMax executable was found in the provided path {max_exe_path}"
        )

    def calculate_execution_parameters(self, max_client_path: str) -> List[str]:
        """
        Provides the complete list of paratemers to run 3dsMax, in function of the configured executable.
        :param max_client_path: The path of the client script to use with 3dsMax.
        :returns: List of string tokens representing the parameters needed to run 3dsMax.
        """
        max_exe: MaxExecutable = self.max_executable
        return [
            max_exe.full_path,
            *self._max_exe_parameters[max_exe.exe_type],
            max_client_path,
        ]

    def is_executable_type(self, executable_type: SupportedMaxExecutable) -> bool:
        """
        Determines if the configured 3dsMax executable corresponds to the provided type.
        :returns: True if the 3dsMax executable is equal to the provided executable type, False otherwise.
        """
        return self.max_executable.exe_type == executable_type
