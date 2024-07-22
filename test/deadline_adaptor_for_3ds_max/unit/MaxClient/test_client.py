# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from unittest.mock import Mock, patch

import pytest
from deadline.max_adaptor.MaxClient.max_client import MaxClient, main


class TestMaxClient:
    @patch("deadline.max_adaptor.MaxClient.max_client.ClientInterface")
    def test_maxclient(self, mock_httpclient: Mock) -> None:
        """Tests that the max client can initialize, set a renderer and close"""
        client = MaxClient(server_path=str(9999))
        client.set_renderer({"renderer": "Default_Scanline_Renderer"})
        client.close()

    @patch("deadline.max_adaptor.MaxClient.max_client.os.path.exists")
    @patch.dict(os.environ, {"MAX_ADAPTOR_SERVER_PATH": "server_path"})
    @patch("deadline.max_adaptor.MaxClient.MaxClient.poll")
    @patch("deadline.max_adaptor.MaxClient.max_client.ClientInterface")
    def test_main(self, mock_httpclient: Mock, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method starts the max client polling method"""
        # GIVEN
        mock_exists.return_value = True

        # WHEN
        main()

        # THEN
        mock_exists.assert_called_once_with("server_path")
        mock_poll.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("deadline.max_adaptor.MaxClient.MaxClient.poll")
    def test_main_no_server_socket(self, mock_poll: Mock) -> None:
        """Tests that the main method raises an OSError if no server path is found"""
        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        assert str(exc_info.value) == (
            "MaxClient cannot connect to the Adaptor because the environment variable "
            "MAX_ADAPTOR_SERVER_PATH does not exist"
        )
        mock_poll.assert_not_called()

    @patch.dict(os.environ, {"MAX_ADAPTOR_SERVER_PATH": "/a/path/that/does/not/exist"})
    @patch("deadline.max_adaptor.MaxClient.max_client.os.path.exists")
    @patch("deadline.max_adaptor.MaxClient.MaxClient.poll")
    def test_main_server_socket_not_exists(self, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method raises an OSError if the server path does not exist"""
        # GIVEN
        mock_exists.return_value = False

        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        mock_exists.assert_called_once_with(os.environ["MAX_ADAPTOR_SERVER_PATH"])
        assert str(exc_info.value) == (
            "MaxClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable MAX_ADAPTOR_SERVER_PATH does not exist. Got: "
            f"{os.environ['MAX_ADAPTOR_SERVER_PATH']}"
        )
        mock_poll.assert_not_called()
