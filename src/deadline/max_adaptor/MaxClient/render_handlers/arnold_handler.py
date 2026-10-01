"""
3ds Max Deadline Cloud Adaptor - Arnold (MAXtoA) specific actions

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import sys
from typing import Any, List, Optional

import pymxs  # noqa
from pymxs import runtime as rt

from .default_max_handler import DefaultMaxHandler

# Re-assign sys stdout and stderr to print in the console instead of the Max Listener
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__


class ArnoldHandler(DefaultMaxHandler):
    """
    Render Handler for Arnold (MAXtoA).

    Arnold AOVs are managed by ``renderer.AOV_Manager`` (an
    ``ArnoldAOVsManager`` reference target), not by 3ds Max's standard render
    element manager. Because of that, the AOV wiring here does NOT go through
    ``RenderElementManager`` the way V-Ray's does; we drive the manager
    directly from the handler. The two things we mutate at render time are
    ``AOV_Manager.outputPath`` (the global AOV output directory) and each
    driver's ``filenameSuffix`` (the basename portion of that driver's output
    file, since Arnold does not include a per-frame token by default).
    """

    def __init__(self):
        """
        Initializes the Arnold Renderer and Arnold Handler.
        """
        super().__init__()
        # Original filenameSuffix for each Arnold AOV driver, captured in driver
        # order the first time _configure_renderer_output runs. Read on every
        # frame to compose the new suffix from the artist's original value
        # (avoids compounding suffixes across frames within a session) and
        # restored in the same order by _restore_arnold_aov_drivers at session end.
        #
        # NOTE: This assumes the driver list is static for the session (same
        # drivers, same order). A single render job's drivers array is expected
        # to be static; if drivers could be added or removed mid-session, switch
        # to keying by driver object identity.
        self._arnold_aov_driver_original_suffixes: List[str] = []
        # Original AOV_Manager.outputPath, captured before the first per-frame
        # override so it can be restored at session end alongside the suffixes.
        # None means "not captured yet" (a captured value is always a str).
        self._arnold_aov_original_output_path: Optional[str] = None

    def check_renderer(self) -> None:
        """
        Ensures Arnold (MAXtoA) is the active renderer, setting it if it isn't.

        Uses ``startswith("Arnold")`` rather than an exact equality check so a
        future versioned class name (e.g. ``Arnold_7_x_x`` if Autodesk ever
        follows V-Ray's naming pattern) still routes here instead of silently
        falling through to Default Scanline.
        """
        current_renderer = str(rt.renderers.current).split(":")[0]
        if not current_renderer.startswith("Arnold"):
            rt.renderers.current = rt.Arnold()

    @staticmethod
    def _normalize_mxs_str(value: Any) -> str:
        """
        Normalize a pymxs string-ish value to a plain ``str``.

        pymxs stringifies unset values as ``"undefined"``, which is not
        guaranteed falsy across MAXtoA versions. Treat both ``None`` and
        ``"undefined"`` (case-insensitive) as an empty string so the sentinel
        never leaks into an output filename or the restore cache.
        """
        if value is None:
            return ""
        text = str(value)
        return "" if text.lower() == "undefined" else text

    def _get_aov_manager(self) -> Optional[Any]:
        """
        Return the Arnold AOV manager, or ``None`` if it isn't available.

        Returns ``Optional[Any]`` because pymxs objects are dynamically typed;
        we can't give a more precise annotation without a stub. Callers should
        treat ``None`` as "AOV manager not accessible" and no-op.
        """
        try:
            return rt.renderers.current.AOV_Manager
        except Exception as exc:
            self.log_to_console(f"Warning: could not access Arnold AOV_Manager: {exc}")
            return None

    def _configure_renderer_output(
        self, output_name: str, output_dir: str, output_format: str
    ) -> bool:
        """
        Align Arnold AOV outputs with the job's output directory and ensure
        per-frame AOV filenames are unique.

        Arnold writes one file per driver under ``AOV_Manager.outputPath``. The
        file's basename is taken from the driver's ``filenameSuffix`` property
        (e.g. ``AOVs`` produces ``AOVs.exr``). With no per-frame component in
        the filename, every frame would overwrite the previous frame's AOV
        output, which is a hard blocker for animation rendering.

        For each frame we:

        1. Force ``AOV_Manager.outputPath`` to the job's output directory so
           AOV files land alongside the main render output (and are picked up
           by job attachments on workers).
        2. Inject the resolved per-frame ``output_name`` into each driver's
           ``filenameSuffix``. The original suffix is preserved as a trailing
           tag so each driver's role is still identifiable, e.g. a driver
           originally suffixed ``AOVs`` produces files named
           ``<output_name>_AOVs.exr``.

        The original ``outputPath`` and each driver's ``filenameSuffix`` are
        cached on the first invocation and restored by
        ``_restore_arnold_aov_drivers`` (invoked from
        ``cleanup_render_elements``) so the scene is not polluted across
        sessions. Per-AOV settings (channel, filter, lightGroup) and
        format-specific driver settings (compression, half precision, color
        space, ...) are left untouched.

        If a driver has an empty ``filenameSuffix`` in the scene, we append
        ``_AOV<index>`` as a per-driver safety tag so it doesn't collide with
        the beauty pass. Because authored suffixes are not guaranteed unique
        (two drivers may share a suffix, or an authored suffix may equal
        another driver's ``_AOV<index>`` tag), uniqueness is enforced
        unconditionally: composed names are tracked per frame and any collision
        is disambiguated with the driver index.

        This method always returns ``False``: the Arnold handler only redirects
        the AOV drivers, it never takes over the beauty pass, so the framework
        must still call ``rt.render(camera=..., outputFile=...)`` to write the
        main render output. (``VrayHandler``, by contrast, returns ``True`` in
        raw-output modes because V-Ray writes the beauty pass into its own
        multichannel container file and the framework must not write it again.)
        """
        aov_mgr = self._get_aov_manager()
        if aov_mgr is None:
            return False

        # Capture the scene's original outputPath once (first frame) so it can
        # be restored at session end, mirroring the per-driver suffix capture.
        if self._arnold_aov_original_output_path is None:
            try:
                self._arnold_aov_original_output_path = self._normalize_mxs_str(aov_mgr.outputPath)
            except Exception as exc:
                self.log_to_console(f"Warning: could not read AOV_Manager.outputPath: {exc}")
                self._arnold_aov_original_output_path = ""

        try:
            aov_mgr.outputPath = output_dir
            self.log_to_console(f"Arnold AOV outputPath set to: {output_dir}")
        except Exception as exc:
            self.log_to_console(f"Warning: failed to set Arnold AOV outputPath: {exc}")

        # Track composed suffixes within this frame so no two drivers ever
        # resolve to the same output filename.
        used_suffixes: set = set()

        for i, drv in enumerate(aov_mgr.drivers):
            # Capture each driver's artist-authored suffix once, in order, on the
            # first frame; restore it at session end.
            if i >= len(self._arnold_aov_driver_original_suffixes):
                try:
                    self._arnold_aov_driver_original_suffixes.append(
                        self._normalize_mxs_str(drv.filenameSuffix)
                    )
                except Exception as exc:
                    self.log_to_console(
                        f"Warning: could not read Arnold driver[{i}].filenameSuffix: {exc}"
                    )
                    self._arnold_aov_driver_original_suffixes.append("")

            original_suffix = self._arnold_aov_driver_original_suffixes[i]
            # Preferred name preserves the authored suffix as a trailing tag;
            # empty suffixes fall back to a per-driver "_AOV<index>" tag.
            base_suffix = (
                f"{output_name}_{original_suffix}" if original_suffix else f"{output_name}_AOV{i}"
            )
            # Authored suffixes are not guaranteed unique, and the _AOV<index>
            # fallback shares a namespace with authored suffixes, so make
            # uniqueness unconditional: on any collision, disambiguate with the
            # driver index (unique per driver). The loop guards the pathological
            # case where a disambiguated name itself collides.
            new_suffix = base_suffix
            while new_suffix in used_suffixes:
                new_suffix = f"{new_suffix}_{i}"
            used_suffixes.add(new_suffix)
            try:
                drv.filenameSuffix = new_suffix
                self.log_to_console(
                    f"Arnold driver[{i}].filenameSuffix: '{original_suffix}' -> '{new_suffix}'"
                )
            except Exception as exc:
                self.log_to_console(
                    f"Warning: failed to set Arnold driver[{i}].filenameSuffix: {exc}"
                )

        return False

    def cleanup_render_elements(self, data: dict) -> None:
        """
        Session-end framework hook.

        The base class's cleanup handles standard 3ds Max render elements.
        Arnold AOVs are a separate subsystem (``AOV_Manager``, not the render
        element manager), but the adaptor only exposes this single per-session
        cleanup hook — so both live here. The AOV work is delegated to
        ``_restore_arnold_aov_drivers`` so its name reflects what it actually
        does.

        Note: the adaptor only enqueues this hook when render-element
        modification is enabled (``enabled_modify_render_elements``). A typical
        Arnold AOV job may not enable it, in which case neither the AOV restore
        nor the standard render-element restore runs. That is acceptable
        because the AOV restore is purely defensive — the worker discards its
        scene copy at session end — but the AOV restore is still wrapped so it
        can never prevent the standard render-element restore from running when
        the hook is enqueued.
        """
        try:
            self._restore_arnold_aov_drivers()
        except Exception as exc:
            self.log_to_console(f"Warning: Arnold AOV restore failed: {exc}")
        super().cleanup_render_elements(data)

    def _restore_arnold_aov_drivers(self) -> None:
        """
        Restore the Arnold AOV state that ``_configure_renderer_output``
        mutated: the ``AOV_Manager.outputPath`` and each driver's
        ``filenameSuffix``, back to the values the scene had before the first
        frame.

        On a worker this is defensive (the scene copy is thrown away at
        session end anyway), but keeps the in-memory scene consistent for
        any code that observes it afterward, and prevents pollution if a
        session ever reuses the handler instance across renders.

        The caches are always cleared even if a restore raises, so the handler
        is left in a clean state.
        """
        if (
            not self._arnold_aov_driver_original_suffixes
            and self._arnold_aov_original_output_path is None
        ):
            return

        aov_mgr = self._get_aov_manager()
        try:
            if aov_mgr is not None:
                if self._arnold_aov_original_output_path is not None:
                    try:
                        aov_mgr.outputPath = self._arnold_aov_original_output_path
                    except Exception as exc:
                        self.log_to_console(
                            f"Warning: failed to restore Arnold AOV_Manager.outputPath: {exc}"
                        )
                # Reading aov_mgr.drivers is itself a pymxs access that can
                # raise; guard it so a failure here can't escape and skip the
                # caller's super().cleanup_render_elements (the standard
                # render-element restore).
                try:
                    drivers = list(aov_mgr.drivers)
                except Exception as exc:
                    self.log_to_console(
                        f"Warning: could not access Arnold AOV drivers for restore: {exc}"
                    )
                    drivers = []
                for i, drv in enumerate(drivers):
                    if i >= len(self._arnold_aov_driver_original_suffixes):
                        break
                    try:
                        drv.filenameSuffix = self._arnold_aov_driver_original_suffixes[i]
                    except Exception as exc:
                        self.log_to_console(
                            f"Warning: failed to restore Arnold driver[{i}].filenameSuffix: {exc}"
                        )
        finally:
            self._arnold_aov_driver_original_suffixes.clear()
            self._arnold_aov_original_output_path = None
