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

except (ImportError, ModuleNotFoundError):
    from deadline.max_adaptor.MaxClient.render_handlers import (  # type: ignore[import]
        get_render_handler,
    )
    from openjd.adaptor_runtime_client import ClientInterface  # type: ignore[import]

logger = logging.getLogger(__name__)

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class MaxClient(ClientInterface):
    def __init__(self, server_path: str) -> None:
        super().__init__(server_path=server_path)
        # List of actions that can be performed by the action queue
        self.actions.update(
            {
                "renderer": self.set_renderer,
                "close": self.close,
                "graceful_shutdown": self.graceful_shutdown,
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
