# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from deadline.max_adaptor.executable_handler import (
    MaxExecutableHandler,
    SupportedMaxExecutable,
)
from unittest.mock import patch, Mock
import os
import pytest
from typing import List


class TestMaxExecutableHandler:

    @pytest.mark.parametrize(
        "max_exe_env_var,expected_max_exe",
        [
            ("3dsmax", "3dsmax"),
            ("3dsmax.exe", "3dsmax"),
            (os.sep.join(["C:", "Users", "user1", "somedir", "3dsmax"]), "3dsmax"),
            (os.sep.join(["C:", "Users", "user1", "somedir", "3dsmax.exe"]), "3dsmax"),
            ("/users/user1/somedir/3dsmax.exe", "3dsmax"),
            ("3dsmaxbatch", "3dsmaxbatch"),
            ("3dsmaxbatch.exe", "3dsmaxbatch"),
            (os.sep.join(["C:", "Users", "user1", "somedir", "3dsmaxbatch"]), "3dsmaxbatch"),
            (os.sep.join(["C:", "Users", "user1", "somedir", "3dsmaxbatch.exe"]), "3dsmaxbatch"),
            ("/users/user1/somedir/3dsmaxbatch.exe", "3dsmaxbatch"),
        ],
    )
    @patch("deadline.max_adaptor.executable_handler.environ")
    def test_executable_calculation_with_valid_exe_path(
        self, mock_environ: Mock, max_exe_env_var: str, expected_max_exe: str
    ) -> None:
        mock_environ.get.return_value = max_exe_env_var
        max_executable_handler: MaxExecutableHandler = MaxExecutableHandler()

        assert max_executable_handler.max_executable.exe_type.value == expected_max_exe

    @pytest.mark.parametrize(
        "max_exe_env_var",
        [
            ("3dsma"),
            ("3dsmax.ex"),
            ("3dsmxbatch"),
            ("3dsmxbatch.xe"),
            (""),
        ],
    )
    @patch("deadline.max_adaptor.executable_handler.environ")
    def test_executable_calculation_with_invalid_exe_path(
        self, mock_environ: Mock, max_exe_env_var: str
    ) -> None:
        mock_environ.get.return_value = max_exe_env_var
        max_executable_handler: MaxExecutableHandler = MaxExecutableHandler()

        with pytest.raises(ValueError):
            max_executable_handler.max_executable

    @pytest.mark.parametrize(
        "max_exe",
        [
            ("3dsmax"),
            ("3dsmaxbatch"),
        ],
    )
    @patch("deadline.max_adaptor.executable_handler.environ")
    def test_calculate_execution_parameters(self, mock_environ: Mock, max_exe: str) -> None:
        mock_environ.get.return_value = max_exe
        max_executable_handler: MaxExecutableHandler = MaxExecutableHandler()
        expected_max_exe: SupportedMaxExecutable = SupportedMaxExecutable(max_exe)
        max_client_path: str = "C:\\test\\max\\client\\path.py"

        execution_parameters: List[str] = max_executable_handler.calculate_execution_parameters(
            max_client_path
        )

        assert expected_max_exe.value in execution_parameters
        assert max_client_path in execution_parameters
        assert set(max_executable_handler._max_exe_parameters[expected_max_exe]).issubset(
            set(execution_parameters)
        )

    @pytest.mark.parametrize(
        "configured_max_exe, max_exe_to_check",
        [
            ("3dsmax", "3dsmax"),
            ("3dsmax", "3dsmaxbatch"),
            ("3dsmaxbatch", "3dsmax"),
            ("3dsmaxbatch", "3dsmaxbatch"),
        ],
    )
    @patch("deadline.max_adaptor.executable_handler.environ")
    def test_is_executable_type(
        self, mock_environ: Mock, configured_max_exe: str, max_exe_to_check: str
    ) -> None:
        mock_environ.get.return_value = configured_max_exe
        max_executable_handler: MaxExecutableHandler = MaxExecutableHandler()
        expected_result: bool = SupportedMaxExecutable(
            configured_max_exe
        ) == SupportedMaxExecutable(max_exe_to_check)

        actual_result: bool = max_executable_handler.is_executable_type(
            SupportedMaxExecutable(max_exe_to_check)
        )

        assert actual_result == expected_result
