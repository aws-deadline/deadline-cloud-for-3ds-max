# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Entry point for V-Ray Standalone submitter UI.
This can be called from MAXScript or directly from Python.
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for V-Ray Standalone submitter.
    """
    try:
        from vray_standalone_submitter import show_vray_standalone_submitter

        _logger.info("Launching V-Ray Standalone submitter...")
        window = show_vray_standalone_submitter()
        return window
    except Exception as e:
        _logger.error(f"Failed to launch V-Ray Standalone submitter: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
