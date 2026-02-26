"""
3ds Max Deadline Cloud Adaptor - All 3dsMax actions needed to make a render using Default Scanline Renderer

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import pymxs  # noqa
from pymxs import runtime as rt

from deadline.max_adaptor.executable_handler import MaxExecutableHandler
from deadline.max_shared.utilities.filename_utils import format_output_filename
from deadline.max_shared.utilities.max_utils import (
    _configure_render_element_filenames,
    _configure_render_element_outputs_filename,
    _set_vray_property,
    get_render_elements,
)

if TYPE_CHECKING:
    from deadline.max_adaptor.MaxClient.render_element_manager import RenderElementManager

logger = logging.getLogger(__name__)

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class DefaultMaxHandler:
    """Render Handler for Default Scanline Renderer"""

    def __init__(self):
        self.action_dict = {
            "start_render": self.start_render,
            "camera": self.set_camera,
            "output_file_path": self.set_output_file_path,
            "output_file_name": self.set_output_file_name,
            "output_file_format": self.set_output_file_format,
            "state_set": self.set_state_set,
            "scene_file": self.set_scene_file,
            # Render elements integration actions
            "configure_render_elements": self.configure_render_elements,
            "cleanup_render_elements": self.cleanup_render_elements,
            # New batch render submission-time actions
            "scene_state": self.set_scene_state,
            "preset_file": self.set_preset_file,
            "pixel_aspect": self.set_pixel_aspect,
        }
        self.camera_node = None
        self.output_dir = None
        self.output_name = None
        self.output_format = None
        self.state_set_name: str = ""
        self._executable_handler: MaxExecutableHandler = MaxExecutableHandler()
        # Initialize render element manager as private attribute
        self._render_element_manager: Optional["RenderElementManager"] = None
        # Path mapping function injected by MaxClient
        # Uses Callable type since map_path comes from ClientInterface
        self.map_path: Optional[Callable[[str], str]] = None

    @property
    def render_element_manager(self) -> Optional["RenderElementManager"]:
        """
        Lazy-loaded render element manager property.

        Returns:
            The render element manager instance, or None if not yet initialized.
        """
        return self._render_element_manager

    @render_element_manager.setter
    def render_element_manager(self, value: Optional["RenderElementManager"]) -> None:
        """
        Setter for the render element manager.

        Args:
            value: The render element manager instance to set.
        """
        self._render_element_manager = value

    def start_render(self, data: dict) -> None:
        """
        Starts a render. Resolves output tokens, calls _configure_renderer for
        renderer-specific setup, then renders.

        Subclasses should override _configure_renderer instead of this method.

        :param data: The data given from the Adaptor. Keys expected: ['frame']
        :type data: dict

        :raises: RuntimeError:
         - If no frame was given,
         - If no camera was set (by init or run data)
         - If no correct output path was given (output_dir, output_name or output_format is missing)
        """
        try:
            frame = data.get("frame")
            if frame is None:
                self.log_to_console("Error: MaxClient: start_render called without a frame number.")
                raise RuntimeError("MaxClient: start_render called without a frame number.")

            if self.output_dir is None or self.output_name is None or self.output_format is None:
                self.log_to_console(
                    "Error: MaxClient: start_render called without a valid output path. Output directory, name or format "
                    "is missing."
                )
                raise RuntimeError(
                    "MaxClient: start_render called without a valid output path. Output directory, name or "
                    "format is missing."
                )

            # Check if render elements were configured during initialization
            render_elements_configured = (
                self.render_element_manager is not None
                and self.render_element_manager.has_render_elements_configured()
            )

            # Set the frame to render
            rt.rendTimeType = 1  # Set to single frame
            rt.sliderTime = frame

            camera = data.get("camera")
            if camera is not None:
                logger.debug("Setting camera with run data")
                camera = self.get_camera_to_render(camera)
                self.camera_node = rt.getNodeByName(camera)

            # If no camera was set by init or run data, use the scene's active camera
            if self.camera_node is None:
                cameras = list(rt.cameras)
                if cameras:
                    self.camera_node = cameras[0]
                    self.log_to_console(
                        f"No camera specified, using scene default: {self.camera_node.name}"
                    )
                else:
                    self.log_to_console("Error: MaxClient: No cameras found in scene.")
                    raise RuntimeError("MaxClient: No cameras found in scene.")

            # Resolve all tokens in the output filename pattern
            scene_name = Path(rt.maxFileName).stem if rt.maxFileName else ""
            state_set_name = self.state_set_name or ""
            # Camera name: prefer run data camera, fall back to init-data camera (self.camera_node)
            if camera:
                camera_name = camera
            elif self.camera_node is not None:
                camera_name = str(self.camera_node.name)
            else:
                camera_name = ""

            output_name = format_output_filename(
                pattern=self.output_name,
                camera_name=camera_name,
                state_set_name=state_set_name,
                scene_name=scene_name,
            )

            output_name = self.reformat_framenumber_padding(output_name, frame)

            # Let subclasses configure renderer-specific settings with the resolved name
            self.log_to_console(
                f"DEBUG start_render: output_dir='{self.output_dir}', output_name='{output_name}', output_format='{self.output_format}'"
            )

            # If output_name is a full path (e.g. from batch view output_filename),
            # extract just the filename portion. The directory comes from self.output_dir.
            output_name = os.path.basename(output_name)

            renderer_handles_output = self._configure_renderer_output(
                output_name=output_name,
                output_dir=self.output_dir,
                output_format=self.output_format,
            )

            output_file = output_name + self.output_format
            output_path = os.path.join(self.output_dir, output_file)

            # Update render element filenames with the resolved output name
            if render_elements_configured:
                self._update_render_element_filenames(output_name)

            # Create the folder(s) if the directory doesn't exist
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            # Not sure if needed?
            if os.path.exists(output_path):
                os.remove(output_path)

            # If the renderer handles its own output (e.g. V-Ray raw/split buffer),
            # don't pass outputFile to rt.render to avoid duplicate files.
            if renderer_handles_output:
                rt.render(camera=self.camera_node, quiet=True)
            else:
                self.log_to_console(f"Rendering to {output_path}")
                rt.render(camera=self.camera_node, outputFile=output_path, quiet=True)

            self.log_to_console(f"MaxClient: Finished Rendering Frame {frame}")

        except Exception:
            # Re-raise the exception after cleanup
            raise
        finally:
            # Restore render elements after rendering if they were configured
            if render_elements_configured:
                try:
                    self.cleanup_render_elements(data)
                except Exception as e:
                    self.log_to_console(f"Warning: Render elements cleanup failed: {e}")

    def _configure_renderer_output(
        self, output_name: str, output_dir: str, output_format: str
    ) -> bool:
        """
        Hook for subclasses to configure renderer-specific settings before rendering.

        Called by start_render after output tokens have been resolved. Subclasses
        should override this instead of start_render to set up renderer-specific
        output paths, render settings, etc.

        :param output_name: The fully resolved output filename (tokens replaced, frame padding applied)
        :param output_dir: The output directory path
        :param output_format: The output file format extension (e.g. ".exr", ".png")
        :returns: True if the renderer handles output file writing (suppresses rt.render outputFile)
        """
        return False

    def reformat_framenumber_padding(self, name: str, number: int) -> str:
        """
        Counts the amount of hashes in the filename and correctly pads the given frame number.

        :param name: the given file name
        :type name: str
        :param number: the given frame number
        :type number: int

        :returns: the updated name
        :return type: str
        """
        padding_amount = name.count("#")

        # If there are no hashes, the submitter decided no frame numbering is needed
        # (e.g. single-frame render). Return the name as-is.
        if not padding_amount:
            return name

        numbers_amount = len(str(number))
        # Calculate how many zeroes need to be added.
        # If the frame number is longer than the padding, no zeroes get added
        zeroes_to_add = padding_amount - numbers_amount
        padded_number = zeroes_to_add * "0" + str(number)
        name = name.replace(padding_amount * "#", padded_number)
        return name

    def _update_render_element_filenames(self, resolved_output_name: str) -> None:
        """
        Configure render element filenames using the resolved output name.

        Render elements are configured during init with the raw output_name pattern
        (which may contain unresolved tokens like <camera>). This method updates
        the render element filenames and V-Ray split buffer path after tokens have
        been resolved at render time.

        :param resolved_output_name: the fully resolved output name (tokens replaced,
            frame padding applied)
        """
        if self.render_element_manager is None or self.output_dir is None:
            return

        output_format = self.output_format or ".png"
        base_filepath = os.path.join(self.output_dir, f"{resolved_output_name}{output_format}")

        render_elements = get_render_elements()
        if not render_elements:
            return

        ignore_list = self.render_element_manager._get_ignore_list(
            self.render_element_manager.cached_settings
        )

        if self.render_element_manager.is_vray:
            # Update V-Ray split buffer filename
            warnings: list[str] = []
            _set_vray_property("output_splitfilename", base_filepath, warnings)
            for w in warnings:
                self.log_to_console(f"Warning: {w}")

            # Update per-element filenames (VRay path)
            warnings = []
            _configure_render_element_filenames(
                render_elements, base_filepath, ignore_list, warnings
            )
            for w in warnings:
                self.log_to_console(f"Warning: {w}")
        else:
            # Update per-element filenames (standard/scanline path)
            warnings = _configure_render_element_outputs_filename(
                render_elements,
                self.output_dir,
                resolved_output_name,
                output_format,
                ignore_list,
            )
            for w in warnings:
                self.log_to_console(f"Warning: {w}")

    def check_renderer(self) -> None:
        """
        Checks if the active renderer is set to Default Scanline Renderer. If it is not, set it to Default Scanline.
        """
        current_renderer = str(rt.renderers.current).split(":")[0]
        if current_renderer != "Default_Scanline_Renderer":
            rt.renderers.current = rt.Default_Scanline_Renderer()

    def set_camera(self, data: dict) -> None:
        """
        Sets the Camera that will be rendered if one was passed along in the init-data.

        :param data: The data given from the Adaptor. Keys expected: ['camera']
        :type data: dict
        """
        logger.debug("Setting camera with init data")
        camera_name = data.get("camera")
        if not camera_name:
            self.log_to_console("No camera specified in init data")
            return
        camera = self.get_camera_to_render(camera_name)
        self.camera_node = rt.getNodeByName(camera)

    def get_camera_to_render(self, camera_name: str) -> str:
        """
        Checks if the camera exists in the scene.

        :param camera_name: the camera we want to check
        :type camera_name: str

        :raises: RuntimeError: If the camera does not exist
        """
        # rt.cameras gives a max collection of cameras
        # Conversion to python list needed
        cameras = rt.cameras
        camera_names = [camera.name for camera in cameras]

        if camera_name not in camera_names:
            self.log_to_console(f"Error: The specified camera, {camera_name}, does not exist.")
            raise RuntimeError(f"The specified camera, {camera_name}, does not exist.")
        return camera_name

    def set_output_file_path(self, data: dict) -> None:
        """
        Sets the output file path.

        Note: Path mapping is already applied by Deadline Cloud to job parameter values
        before they reach the adaptor, so no additional mapping is needed here.

        :param data: The data given from the Adaptor. Keys expected: ['output_file_path']
        :type data: dict
        """
        logger.debug("setting output path")
        render_dir = data.get("output_file_path")
        if render_dir:
            self.output_dir = render_dir

    def set_output_file_name(self, data: dict) -> None:
        """
        Sets the output filename.

        :param data: The data given from the Adaptor. Keys expected: ['output_file_name']
        :type data: dict
        """
        logger.debug("setting output name")
        name = data.get("output_file_name")
        if name:
            self.output_name = name

    def set_output_file_format(self, data: dict) -> None:
        """
        Sets the output file format.

        :param data: The data given from the Adaptor. Keys expected: ['output_file_format']
        :type data: dict
        """
        logger.debug("setting output format")
        format_ = data.get("output_file_format")
        if format_:
            self.output_format = format_

    def set_state_set(self, data: dict) -> None:
        """
        Sets the state set.

        :param data: The data given from the Adaptor. Keys expected: ['state_set']
        :type data: dict

        :raises: RuntimeError: if state set doesn't exist
        """
        state_set_name = data.get("state_set")
        self.state_set_name = state_set_name or ""

        # Create necessary items to interact with state sets
        state_sets_dot_net_object = rt.dotNetObject("Autodesk.Max.StateSets.Plugin")
        state_sets_instance = state_sets_dot_net_object.Instance
        master_state = state_sets_instance.EntityManager.RootEntity.MasterStateSet

        state_sets = []
        need_state: int
        # Loop over all state sets in the scene to get the correct index
        # Note: 3dsMax has a weird indexing system, so we start at -1.
        # Note: The last item in the list is a default 'Objects' state, where (unless manually changed) all objects are
        #  set to hidden. We don't want to include this state set in our iteration
        for i in range(-1, master_state.Children.count - 2):
            state_sets.append([master_state.Children.Item[i].Name, i + 1])
            if master_state.Children.Item[i].Name == state_set_name:
                need_state = i + 1

        # Set the current state set
        try:
            # Setting the state set only works in MaxScript
            rt.execute(
                f"stateSetsDotNetObject = dotNetObject "
                f'"Autodesk.Max.StateSets.Plugin" \n'
                f"stateSets = stateSetsDotNetObject.Instance \n"
                f"masterState = stateSets.EntityManager.RootEntity."
                f"MasterStateSet \n"
                f"needState = masterState.Children.Item[{need_state}]\n"
                f"masterState.CurrentState = #(needState)"
            )
        except NameError:
            self.log_to_console(
                f"Error: The specified state set, '{state_set_name}', does not exist."
            )
            raise RuntimeError(f"The specified state set, '{state_set_name}', does not exist.")
        else:
            self.log_to_console(f"Set state set to: {state_set_name}")

        self.check_renderer()

    def set_scene_state(self, data: dict) -> None:
        """
        Restore a scene state via rt.sceneStateMgr.

        This is distinct from set_state_set which uses the Autodesk.Max.StateSets.Plugin API.
        Scene states are used in batch render mode, while state sets are used in default mode.

        :param data: The data given from the Adaptor. Keys expected: ['scene_state']
        :type data: dict

        :raises RuntimeError: If the scene state does not exist or fails to restore
        """
        scene_state_name = data.get("scene_state")
        if not scene_state_name:
            return
        scene_state_mgr = rt.sceneStateMgr
        index = scene_state_mgr.FindSceneState(scene_state_name)
        if index < 0:
            raise RuntimeError(f"Scene State '{scene_state_name}' does not exist in the scene")
        result = scene_state_mgr.RestoreAllParts(scene_state_name)
        if not result:
            raise RuntimeError(f"Failed to restore scene state '{scene_state_name}'")
        self.log_to_console(f"Applied scene state: {scene_state_name}")

    def set_preset_file(self, data: dict) -> None:
        """
        Load a render preset file with path mapping.

        :param data: The data given from the Adaptor. Keys expected: ['preset_file']
        :type data: dict

        :raises RuntimeError: If the preset file does not exist after path mapping or fails to load
        """
        preset_path = data.get("preset_file")
        if not preset_path:
            return
        if self.map_path is not None:
            preset_path = self.map_path(preset_path)
        if not os.path.exists(preset_path):
            raise RuntimeError(f"Preset file '{preset_path}' does not exist after path mapping")
        result = rt.renderPresets.LoadAll(0, preset_path)
        if not result:
            raise RuntimeError(
                f"Failed to load preset file '{preset_path}' — may be incompatible with current renderer"
            )
        self.log_to_console(f"Loaded render preset: {preset_path}")

    def set_pixel_aspect(self, data: dict) -> None:
        """
        Set the render pixel aspect ratio.

        :param data: The data given from the Adaptor. Keys expected: ['pixel_aspect']
        :type data: dict

        :raises RuntimeError: If the pixel aspect value is not a positive number
        """
        pixel_aspect_str = data.get("pixel_aspect")
        if not pixel_aspect_str:
            return
        try:
            pixel_aspect = float(pixel_aspect_str)
        except (ValueError, TypeError):
            raise RuntimeError(f"Invalid pixel aspect: '{pixel_aspect_str}' (not a number)")
        if pixel_aspect <= 0:
            raise RuntimeError(f"Invalid pixel aspect: {pixel_aspect} (must be a positive number)")
        rt.renderPixelAspect = pixel_aspect
        self.log_to_console(f"Set pixel aspect: {pixel_aspect}")

    def set_scene_file(self, data: dict) -> None:
        """
        Opens a scene file in 3dsMax in quiet mode. This means that any popups after start up get ignored
        (e.g. missing XRefs) so they don't halt the adaptor.

        :param data: The data given from the Adaptor. Keys expected: ['scene_file']

        :raises: FileNotFoundError: If the file provided in the data dictionary does not exist.
        """
        logger.debug("opening max scene")
        file_path = data.get("scene_file", "")
        if not os.path.isfile(file_path):
            self.log_to_console(f"Error: The scene file '{file_path}' does not exist")
            raise FileNotFoundError(f"Error: The scene file '{file_path}' does not exist")
        try:
            rt.SetQuietMode(True)
            # Make sure any renderered frames are re-rendered.
            rt.skipRenderedFrames = False
            rt.loadMaxFile(file_path, quiet=True)

            # Apply path mapping after scene load
            if self.map_path is not None:
                self._apply_path_mapping()

        except Exception:
            self.log_to_console(f"Error: while opening '{file_path}'")
            raise RuntimeError(f"Error: while opening '{file_path}'")

    def _apply_path_mapping(self) -> None:
        """
        Applies path mapping to scene assets after scene load.
        Override in subclasses to handle renderer-specific assets.
        """
        pass  # Base implementation does nothing

    def log_to_console(self, message: str) -> None:
        """
        Log message to both stdout and Max.log file.
        Delegates to module-level log_to_console function.

        :param message: The text to log
        """
        log_to_console(message)

    def configure_render_elements(self, data: dict) -> None:
        """
        Configure render elements using the render element manager directly.

        :param data: The data containing render elements configuration
        :raises: RuntimeError if configuration fails
        """
        try:
            # Lazy initialize render element manager to avoid circular imports
            if self.render_element_manager is None:
                from deadline.max_adaptor.MaxClient.render_element_manager import (
                    RenderElementManager,
                )

                self.render_element_manager = RenderElementManager(
                    output_file_path=self.output_dir,
                    output_file_name=self.output_name,
                    output_file_format=self.output_format,
                )

            result = self.render_element_manager.configure_render_elements(data)
            if not result.success:
                error_msg = result.error or "Unknown error"
                self.log_to_console(f"Error: Render elements configuration failed: {error_msg}")
                raise RuntimeError(f"Render elements configuration failed: {error_msg}")
            else:
                # Log success message
                success_msg = result.message or "Render elements configured successfully"
                self.log_to_console(f"Render elements configuration: {success_msg}")

                # Log warnings if any
                if result.warnings:
                    for warning in result.warnings:
                        self.log_to_console(f"Warning: {warning}")

                # Log element count if available
                if result.element_count is not None:
                    self.log_to_console(f"Configured {result.element_count} render elements")
        except Exception as e:
            self.log_to_console(f"Error configuring render elements: {e}")
            raise RuntimeError(f"Render elements configuration failed: {e}")

    def cleanup_render_elements(self, data: dict) -> None:
        """
        Cleanup render elements after rendering completes.
        Uses the render element manager's cached configuration.

        :param data: The run data (not used for render elements cleanup)
        """
        # Check if render element manager exists and was configured
        if (
            self.render_element_manager is None
            or not self.render_element_manager.has_render_elements_configured()
        ):
            self.log_to_console("No render element configuration found, skipping cleanup")
            return

        try:
            self.log_to_console("Cleaning up render elements after rendering")
            result = self.render_element_manager.restore_render_elements()
            if result.success:
                success_msg = result.message or "Render elements cleanup completed successfully"
                self.log_to_console(f"Render elements cleanup: {success_msg}")

                # Log warnings if any
                if result.warnings:
                    for warning in result.warnings:
                        self.log_to_console(f"Warning: {warning}")
            else:
                error_msg = result.error or "Unknown error"
                self.log_to_console(f"Warning: Render elements cleanup had issues: {error_msg}")
        except Exception as e:
            self.log_to_console(f"Warning: Error during render elements cleanup: {e}")


def log_to_console(message: str) -> None:
    """
    Log message to both stdout and Max.log file.

    :param message: The text to log
    """
    # When using 3dsmaxbatch (batch mode), log to Max.log file only
    try:
        # When using 3dsmax (interactive mode), print to stdout
        print(message, flush=True)
        rt.logsystem.logEntry(message, broadcast=True)
    except Exception:
        # If logsystem fails, continue without breaking execution
        pass
