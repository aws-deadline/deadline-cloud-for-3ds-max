# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from deadline.max_adaptor.MaxAdaptor.regex_callback_handler import MaxRegexCallback
from unittest.mock import patch, Mock


class TestMaxRegexCallback:

    @patch("deadline.max_adaptor.MaxAdaptor.regex_callback_handler.RegexCallback.get_match")
    def test_get_match_removes_extra_characters(self, mock_regex_callback: Mock) -> None:
        max_regex_callback: MaxRegexCallback = MaxRegexCallback([], None)

        max_regex_callback.get_match("\x00\x00a\x00\x00\x00\x00\x00b\x00\x00\x00c\x00")

        mock_regex_callback.assert_called_once_with("abc")
