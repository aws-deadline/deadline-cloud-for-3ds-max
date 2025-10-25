"""
3ds Max Deadline Cloud Adaptor - Logger Interceptor

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import logging
import sys
from typing import Callable, List, Optional

from pymxs import runtime as rt

from deadline.max_adaptor.executable_handler import MaxExecutableHandler, SupportedMaxExecutable

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class ConsoleLogHandler(logging.Handler):
    """Custom logging handler that routes logs to both console and Max.log file."""

    def __init__(self, log_to_console_func: Callable[[str], None]):
        super().__init__()
        self.log_to_console_func = log_to_console_func
        # Set a formatter for better log formatting
        formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit a log record by sending it to both console and Max.log."""
        try:
            msg = self.format(record)
            # Send to console (stdout)
            self.log_to_console_func(msg)
            # Also send to Max.log file via logsystem
            import pymxs

            pymxs.runtime.logsystem.logEntry(msg, broadcast=True)
        except Exception:
            # Avoid infinite recursion if logging fails
            pass


class LoggerInterceptor:
    """
    Logger interceptor for capturing and routing render element manager logs.

    This class manages the setup and teardown of custom log handlers to ensure
    that logs from the render element manager and related utilities are properly
    routed to both console output and the 3ds Max log file.
    """

    def __init__(self):
        self._console_handler: Optional[ConsoleLogHandler] = None
        self._intercepted_loggers: List[logging.Logger] = []
        self._executable_handler: MaxExecutableHandler = MaxExecutableHandler()

    def setup(self) -> None:
        """
        Set up logger interceptor to capture render element manager logs.
        """
        if self._console_handler is not None:
            return  # Already set up

        # Create console handler
        self._console_handler = ConsoleLogHandler(self._log_to_console)
        self._console_handler.setLevel(logging.DEBUG)

        # List of logger names to intercept
        logger_names = [
            "max_adaptor.MaxClient.render_element_manager",
            "deadline.max_shared.utilities.max_utils",
            # Add the root logger name from render_element_manager.py
            "deadline.max_adaptor.MaxClient.render_element_manager",
        ]

        # Add handler to relevant loggers
        for logger_name in logger_names:
            target_logger = logging.getLogger(logger_name)
            # Check if handler is already added to avoid duplicates
            if self._console_handler not in target_logger.handlers:
                target_logger.addHandler(self._console_handler)
                target_logger.setLevel(logging.DEBUG)  # Ensure we capture DEBUG level logs
                self._intercepted_loggers.append(target_logger)

        self._log_to_console("Logger interceptor set up for render element manager")

    def teardown(self) -> None:
        """
        Tear down logger interceptor.
        """
        if self._console_handler is None:
            return  # Not set up

        # Remove handler from all intercepted loggers
        for target_logger in self._intercepted_loggers:
            target_logger.removeHandler(self._console_handler)

        # Clear references
        self._intercepted_loggers.clear()
        self._console_handler = None

        self._log_to_console("Logger interceptor torn down")

    def _log_to_console(self, message: str) -> None:
        """
        Handles logging to both stdout and Max.log file for better debugging.
        :param message: The text to log to the stdout and Max.log.
        """
        # When using 3dsmaxbatch (batch mode), log to Max.log file only
        if self._executable_handler.is_executable_type(SupportedMaxExecutable.BATCH):
            try:
                rt.logsystem.logEntry(message, broadcast=True)
            except Exception:
                # If logsystem fails, continue without breaking execution
                pass
        else:
            # When using 3dsmax (interactive mode), print to stdout
            print(message, flush=True)
