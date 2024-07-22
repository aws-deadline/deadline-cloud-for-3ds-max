"""
3ds Max Deadline Cloud Adaptor - All 3dsMax actions needed to make a render using Default Scanline Renderer

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

from __future__ import annotations

import logging
import os
import sys

import pymxs  # noqa
from pymxs import runtime as rt

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
        }
        self.camera_node = None
        self.output_dir = None
        self.output_name = None
        self.output_format = None

    def start_render(self, data: dict) -> None:
        """
        Starts a render in the scanline renderer.

        :param data: The data given from the Adaptor. Keys expected: ['frame']
        :type data: dict

        :raises: RuntimeError:
         - If no frame was given,
         - If no camera was set (by init or run data)
         - If no correct output path was given (output_dir, output_name or output_format is missing)
        """
        frame = data.get("frame")
        if frame is None:
            print("Error: MaxClient: start_render called without a frame number.")
            raise RuntimeError("MaxClient: start_render called without a frame number.")

        if self.output_dir is None or self.output_name is None or self.output_format is None:
            print(
                "Error: MaxClient: start_render called without a valid output path. Output directory, name or format "
                "is missing."
            )
            raise RuntimeError(
                "MaxClient: start_render called without a valid output path. Output directory, name or "
                "format is missing."
            )

        # Set the frame to render
        rt.rendTimeType = 1  # Set to single frame
        rt.sliderTime = frame

        output_name = ""
        camera = data.get("camera")
        if camera is not None:
            logger.debug("Setting camera with run data")
            camera = self.get_camera_to_render(camera)
            self.camera_node = rt.getNodeByName(camera)
            # If camera gets set by run data, add the camera to the output name
            output_name = self.output_name + "_" + camera

        # Since camera can be set by both init and run data, this isn't a required parameter in either schema.
        if self.camera_node is None:
            print("Error: MaxClient: start_render called without a camera.")
            raise RuntimeError("MaxClient: start_render called without a camera.")

        # Create output path to pass along with render
        if not output_name:
            output_name = self.reformat_framenumber_padding(self.output_name, frame)
        else:
            output_name = self.reformat_framenumber_padding(output_name, frame)
        output_file = output_name + self.output_format
        output_path = os.path.join(self.output_dir, output_file)

        # Create the folder(s) if the directory doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Not sure if needed?
        if os.path.exists(output_path):
            os.remove(output_path)

        rt.render(camera=self.camera_node, outputFile=output_path)

        print(f"MaxClient: Finished Rendering Frame {frame}\n", flush=True)

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

        # If there are no hashes indicating the padding, just add the number
        if not padding_amount:
            return name + str(number)

        numbers_amount = len(str(number))
        # Calculate how many zeroes need to be added.
        # If the frame number is longer than the padding, no zeroes get added
        zeroes_to_add = padding_amount - numbers_amount
        padded_number = zeroes_to_add * "0" + str(number)
        name = name.replace(padding_amount * "#", padded_number)
        return name

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
            print("No camera specified in init data")
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
            print(f"Error: The specified camera, {camera_name}, does not exist.")
            raise RuntimeError(f"The specified camera, {camera_name}, does not exist.")
        return camera_name

    def set_output_file_path(self, data: dict) -> None:
        """
        Sets the output file path.

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
            print(f"Error: The specified state set, '{state_set_name}', does not exist.")
            raise RuntimeError(f"The specified state set, '{state_set_name}', does not exist.")

        self.check_renderer()

    def set_scene_file(self, data: dict):
        """
        Opens a scene file in 3dsMax in quiet mode. This means that any popups after start up get ignored
        (e.g. missing XRefs) so they don't halt the adaptor.

        :param data: The data given from the Adaptor. Keys expected: ['scene_file']

        :raises: FileNotFoundError: If the file provided in the data dictionary does not exist.
        """
        logger.debug("opening max scene")
        file_path = data.get("scene_file", "")
        if not os.path.isfile(file_path):
            print(f"Error: The scene file '{file_path}' does not exist")
            raise FileNotFoundError(f"Error: The scene file '{file_path}' does not exist")
        try:
            rt.SetQuietMode(True)
            rt.loadMaxFile(file_path, quiet=True)
        except Exception:
            print(f"Error: while opening '{file_path}'")
            raise RuntimeError(f"Error: while opening '{file_path}'")
