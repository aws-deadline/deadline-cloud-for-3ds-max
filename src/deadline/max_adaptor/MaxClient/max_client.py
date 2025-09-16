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

except (ImportError, ModuleNotFoundError):
    from deadline.max_adaptor.MaxClient.render_handlers import (  # type: ignore[import]
        get_render_handler,
    )
    from deadline.max_adaptor.MaxClient.render_element_manager import (  # type: ignore[import]
        RenderElementManager,
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
        render_handler = get_render_handler(renderer["renderer"])

        self.actions.update(render_handler.action_dict)

    def close(self, args: Optional[dict] = None) -> None:
        rt.execute("quitmax #noprompt")

    def graceful_shutdown(self, signum: int, frame: FrameType | None):
        rt.execute("quitmax #noprompt")

    def configure_render_elements(self, data: dict) -> dict:
        """
        Configure comprehensive render elements settings using pymxs.

        This method handles all render element configuration including:
        - Basic enable/disable settings
        - Ignore settings (by name)
        - Path and filename updates with naming patterns
        - V-Ray VFB integration and split buffer support

        Args:
            data: Dictionary containing render element configuration parameters

        Returns:
            Dictionary with success status and any messages/errors
        """
        try:
            logger.info("Configuring render elements")
            result = self.render_element_manager.configure_render_elements(data)

            if result.get("success"):
                logger.info(f"Render elements configured: {result.get('message', '')}")
            else:
                logger.error(f"Render elements configuration failed: {result.get('error', '')}")

            return result

        except Exception as e:
            logger.error(f"Exception in configure_render_elements: {e}")
            return {"success": False, "error": str(e)}

    def validate_render_elements(self, data: dict) -> dict:
        """
        Validate render element configuration without making changes.

        Args:
            data: Dictionary containing render element configuration parameters

        Returns:
            Dictionary with validation results
        """
        try:
            logger.info("Validating render elements configuration")
            result = self.render_element_manager.validate_render_elements(data)

            if result.get("success"):
                element_count = result.get("element_count", 0)
                warnings = result.get("warnings", [])
                logger.info(
                    f"Validation completed: {element_count} elements, {len(warnings)} warnings"
                )
            else:
                logger.error(f"Render elements validation failed: {result.get('error', '')}")

            return result

        except Exception as e:
            logger.error(f"Exception in validate_render_elements: {e}")
            return {"success": False, "error": str(e)}

    def restore_render_elements(self, data: Optional[dict] = None) -> dict:
        """
        Restore render elements to their original state.

        Args:
            data: Optional configuration data (unused but kept for interface consistency)

        Returns:
            Dictionary with restoration results
        """
        try:
            logger.info("Restoring render elements to original state")
            result = self.render_element_manager.restore_render_elements(data)

            if result.get("success"):
                logger.info(f"Render elements restored: {result.get('message', '')}")
            else:
                logger.error(f"Render elements restoration failed: {result.get('error', '')}")

            return result

        except Exception as e:
            logger.error(f"Exception in restore_render_elements: {e}")
            return {"success": False, "error": str(e)}


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
