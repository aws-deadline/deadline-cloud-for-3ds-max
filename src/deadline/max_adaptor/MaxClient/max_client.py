"""
3ds Max Deadline Cloud Adaptor - 3dsMax Client Interface

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

from __future__ import annotations

import logging
import os
import sys
from types import FrameType
from typing import Optional

import pymxs  # noqa
from pymxs import runtime as rt

# The Max Adaptor adds the `openjd` namespace directory to PYTHONPATH, so that importing just the
# adaptor_runtime_client should work.
try:
    from adaptor_runtime_client import ClientInterface  # type: ignore[import]

    from max_adaptor.MaxClient.render_handlers import (  # type: ignore[import]
        get_render_handler,
    )
    from max_adaptor.MaxClient.render_element_manager import (  # type: ignore[import]
        RenderElementManager,
    )
    from max_adaptor.MaxClient.logger_interceptor import (  # type: ignore[import]
        LoggerInterceptor,
    )

except (ImportError, ModuleNotFoundError):
    from deadline.max_adaptor.MaxClient.render_handlers import (  # type: ignore[import]
        get_render_handler,
    )
    from deadline.max_adaptor.MaxClient.render_element_manager import (  # type: ignore[import]
        RenderElementManager,
    )
    from deadline.max_adaptor.MaxClient.logger_interceptor import (  # type: ignore[import]
        LoggerInterceptor,
    )
    from openjd.adaptor_runtime_client import ClientInterface  # type: ignore[import]

logger = logging.getLogger(__name__)

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class MaxClient(ClientInterface):
    def __init__(self, server_path: str) -> None:
        super().__init__(server_path=server_path)

        # Initialize render element manager for comprehensive render elements support
        self.render_element_manager = RenderElementManager()

        # Initialize logger interceptor for render element logging
        self.logger_interceptor = LoggerInterceptor()

        # List of actions that can be performed by the action queue
        self.actions.update(
            {
                "renderer": self.set_renderer,
                "close": self.close,
                "graceful_shutdown": self.graceful_shutdown,
                # Enhanced render elements actions
                "configure_render_elements": self.configure_render_elements,
                "validate_render_elements": self.validate_render_elements,
                "restore_render_elements": self.restore_render_elements,
            }
        )

    def set_renderer(self, renderer: dict):
        """
        Determines which render handler to use.
        """
        logger.debug("setting render handler")

        # Set up logger interceptor when renderer is set
        self.logger_interceptor.setup()

        render_handler = get_render_handler(renderer["renderer"])

        self.actions.update(render_handler.action_dict)

    def close(self, args: Optional[dict] = None) -> None:
        # Tear down logger interceptor before closing
        self.logger_interceptor.teardown()
        rt.execute("quitmax #noprompt")

    def graceful_shutdown(self, signum: int, frame: FrameType | None):
        # Tear down logger interceptor before shutdown
        self.logger_interceptor.teardown()
        rt.execute("quitmax #noprompt")

    def configure_render_elements(self, data: dict) -> None:
        """
        Configure comprehensive render elements settings using pymxs.

        This method handles all render element configuration including:
        - Basic enable/disable settings
        - Ignore settings (by name)
        - Path and filename updates with naming patterns
        - V-Ray VFB integration and split buffer support

        Args:
            data: Dictionary containing render element configuration parameters
        """
        try:
            logger.info("Configuring render elements")
            result = self.render_element_manager.configure_render_elements(data)

            if result.success:
                logger.info(f"Render elements configured: {result.message or ''}")
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"Configuration warning: {warning}")
            else:
                logger.error(f"Render elements configuration failed: {result.error or ''}")

        except Exception as e:
            logger.error(f"Exception in configure_render_elements: {e}")
            return

    def validate_render_elements(self, data: dict) -> None:
        """
        Validate render element configuration without making changes.

        Args:
            data: Dictionary containing render element configuration parameters
        """
        try:
            logger.info("Validating render elements configuration")
            result = self.render_element_manager.validate_render_elements(data)

            if result.success:
                element_count = result.element_count or 0
                warnings = result.warnings or []
                logger.info(
                    f"Validation completed: {element_count} elements, {len(warnings)} warnings"
                )
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"Validation warning: {warning}")
            else:
                logger.error(f"Render elements validation failed: {result.error or ''}")

        except Exception as e:
            logger.error(f"Exception in validate_render_elements: {e}")
            return

    def restore_render_elements(self, data: Optional[dict] = None) -> None:
        """
        Restore render elements to their original state.

        Args:
            data: Optional configuration data (unused but kept for interface consistency)
        """
        try:
            logger.info("Restoring render elements to original state")
            result = self.render_element_manager.restore_render_elements(data)

            if result.success:
                logger.info(f"Render elements restored: {result.message or ''}")
                if result.warnings:
                    for warning in result.warnings:
                        logger.warning(f"Restoration warning: {warning}")
            else:
                logger.error(f"Render elements restoration failed: {result.error or ''}")

        except Exception as e:
            logger.error(f"Exception in restore_render_elements: {e}")
            return


def main():
    """
    Initializes the 3ds Max Client Interface if a server path was set.
    """
    server_path = os.environ.get("MAX_ADAPTOR_SERVER_PATH")
    if not server_path:
        print(
            "Error: MaxClient cannot connect to the Adaptor because the environment variable "
            "MAX_ADAPTOR_SERVER_PATH does not exist"
        )
        raise OSError(
            "MaxClient cannot connect to the Adaptor because the environment variable MAX_ADAPTOR_SERVER_PATH "
            "does not exist"
        )

    if not os.path.exists(server_path):
        print(
            "Error: MaxClient cannot connect to the Adaptor because the socket at the path defined by the "
            "environment variable MAX_ADAPTOR_SERVER_PATH does not exist. Got: "
            f"{os.environ['MAX_ADAPTOR_SERVER_PATH']}"
        )
        raise OSError(
            "MaxClient cannot connect to the Adaptor because the socket at the path defined by the environment "
            f"variable MAX_ADAPTOR_SERVER_PATH does not exist. Got: {os.environ['MAX_ADAPTOR_SERVER_PATH']}"
        )

    client = MaxClient(server_path)
    client.poll()


if __name__ == "__main__":  # pragma: no cover
    logger.debug("starting max client")
    main()
