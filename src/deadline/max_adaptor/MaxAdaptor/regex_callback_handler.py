"""
3ds Max Deadline Cloud Adaptor - 3dsMax Regex Callback Handler

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

from __future__ import annotations
import re
from openjd.adaptor_runtime.app_handlers import RegexCallback


class MaxRegexCallback(RegexCallback):

    def __init__(
        self, regex_list, callback, exit_if_matched=False, only_run_if_first_matched=False
    ):
        super().__init__(regex_list, callback, exit_if_matched, only_run_if_first_matched)

    def get_match(self, msg: str) -> re.Match | None:
        """
        Takes care of a special case in 3dsMax, in which unexpected characters are added to executable output.
        The rest of the functionality is the as in the parent class.
        :param msg: The text to parse.
        """
        return super().get_match(msg.replace("\x00", ""))
