# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for ArnoldHandler AOV path mapping and output configuration."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from deadline.max_adaptor.MaxClient.render_handlers.default_max_handler import (
    DefaultMaxHandler,
)


def _make_drivers(suffixes):
    """Build a list of mock driver objects with the given filenameSuffix values."""
    drivers = []
    for suffix in suffixes:
        driver = MagicMock(name=f"driver_{suffix}")
        driver.filenameSuffix = suffix
        drivers.append(driver)
    return drivers


@contextmanager
def _handler_with_aov_manager(outputPath: str, driver_suffixes=None):
    """
    Yield ``(handler, aov_manager_mock, drivers)`` with ``rt`` (and its
    ``renderers.current.AOV_Manager``) mocked for the duration of the ``with``
    block. The rt patch is always stopped on exit, even if the test raises.
    """
    with patch("deadline.max_adaptor.MaxClient.render_handlers.arnold_handler.rt") as mock_rt:
        drivers = _make_drivers(driver_suffixes or [])
        aov_mgr = MagicMock(name="AOV_Manager")
        aov_mgr.outputPath = outputPath
        aov_mgr.drivers = drivers
        mock_rt.renderers.current.AOV_Manager = aov_mgr

        from deadline.max_adaptor.MaxClient.render_handlers.arnold_handler import (
            ArnoldHandler,
        )

        yield ArnoldHandler(), aov_mgr, drivers


class TestArnoldHandlerConfigureRendererOutput:
    """Tests for ArnoldHandler._configure_renderer_output (frame-unique AOV filenames)."""

    def test_sets_aov_output_path_and_per_frame_filename_suffixes(self) -> None:
        with _handler_with_aov_manager(
            outputPath="C:/scene_baked_path",
            driver_suffixes=["AOVs", "AOVs_1", "AOVs_2"],
        ) as (handler, aov_mgr, drivers):
            result = handler._configure_renderer_output(
                output_name="cam_state_render0001",
                output_dir="C:/Sessions/job_output",
                output_format=".exr",
            )

            assert aov_mgr.outputPath == "C:/Sessions/job_output"
            # Each driver gets its suffix prefixed with the resolved per-frame name,
            # preserving the original suffix as a tag so drivers stay identifiable.
            assert drivers[0].filenameSuffix == "cam_state_render0001_AOVs"
            assert drivers[1].filenameSuffix == "cam_state_render0001_AOVs_1"
            assert drivers[2].filenameSuffix == "cam_state_render0001_AOVs_2"
            # Original suffixes should be cached for cleanup
            assert handler._arnold_aov_driver_original_suffixes == [
                "AOVs",
                "AOVs_1",
                "AOVs_2",
            ]
            # Beauty pass still flows through the framework
            assert result is False

    def test_caches_original_suffix_only_once_across_frames(self) -> None:
        """Multi-frame jobs call _configure_renderer_output per frame; cache once."""
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["AOVs"]) as (
            handler,
            _,
            drivers,
        ):
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")
            assert drivers[0].filenameSuffix == "frame_0_AOVs"

            # Second frame: cache must NOT be replaced with the already-mutated value.
            handler._configure_renderer_output("frame_1", "C:/out", ".exr")
            assert drivers[0].filenameSuffix == "frame_1_AOVs"
            assert handler._arnold_aov_driver_original_suffixes == ["AOVs"]

    def test_empty_original_suffix_uses_indexed_aov_safety_tag(self) -> None:
        """
        When the driver's original suffix is empty we still need to
        distinguish AOV output from the beauty pass; a per-driver "_AOV<index>"
        tag is appended so filenames don't collide.
        """
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=[""]) as (
            handler,
            _,
            drivers,
        ):
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")

            assert drivers[0].filenameSuffix == "frame_0_AOV0"

    def test_multiple_empty_suffix_drivers_do_not_collide(self) -> None:
        """
        Two drivers with empty suffixes must produce distinct filenames — the
        index-based safety tag keeps them from overwriting each other.
        """
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["", ""]) as (
            handler,
            _,
            drivers,
        ):
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")

            assert drivers[0].filenameSuffix == "frame_0_AOV0"
            assert drivers[1].filenameSuffix == "frame_0_AOV1"
            assert drivers[0].filenameSuffix != drivers[1].filenameSuffix

    def test_duplicate_authored_suffixes_do_not_collide(self) -> None:
        """
        Two drivers with the same non-empty authored suffix must not compose to
        the same filename; the second is disambiguated with the driver index.
        """
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["AOVs", "AOVs"]) as (
            handler,
            _,
            drivers,
        ):
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")

            assert drivers[0].filenameSuffix == "frame_0_AOVs"
            assert drivers[1].filenameSuffix == "frame_0_AOVs_1"
            assert drivers[0].filenameSuffix != drivers[1].filenameSuffix

    def test_authored_suffix_colliding_with_safety_tag_is_disambiguated(self) -> None:
        """
        An authored suffix that equals another driver's "_AOV<index>" safety tag
        must still resolve to a distinct filename.
        """
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["", "AOV0"]) as (
            handler,
            _,
            drivers,
        ):
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")

            # driver[0] empty -> "frame_0_AOV0"; driver[1] authored "AOV0"
            # composes to the same base and is disambiguated with its index.
            assert drivers[0].filenameSuffix == "frame_0_AOV0"
            assert drivers[1].filenameSuffix == "frame_0_AOV0_1"
            assert drivers[0].filenameSuffix != drivers[1].filenameSuffix

    def test_undefined_suffix_is_treated_as_empty(self) -> None:
        """
        pymxs stringifies an unset suffix as "undefined"; it must be normalized
        to empty (falling back to the "_AOV<index>" tag) and cached as "" so the
        literal "undefined" never lands in a filename or the restore cache.
        """
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["undefined"]) as (
            handler,
            _,
            drivers,
        ):
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")

            assert drivers[0].filenameSuffix == "frame_0_AOV0"
            assert handler._arnold_aov_driver_original_suffixes == [""]

    @pytest.mark.parametrize("driver_count", [0, 1, 3])
    def test_returns_false(self, driver_count: int) -> None:
        with _handler_with_aov_manager(
            outputPath="C:/baked",
            driver_suffixes=[f"AOVs_{i}" for i in range(driver_count)],
        ) as (handler, _, _drivers):
            result = handler._configure_renderer_output("name", "C:/out", ".exr")
            assert result is False

    def test_returns_false_when_aov_manager_missing(self) -> None:
        with patch("deadline.max_adaptor.MaxClient.render_handlers.arnold_handler.rt") as mock_rt:
            mock_rt.renderers.current.AOV_Manager = None

            from deadline.max_adaptor.MaxClient.render_handlers.arnold_handler import (
                ArnoldHandler,
            )

            handler = ArnoldHandler()
            result = handler._configure_renderer_output("frame_0", "C:/out", ".exr")
            assert result is False


class TestArnoldHandlerCleanup:
    """Tests for ArnoldHandler.cleanup_render_elements (suffix restoration)."""

    def test_cleanup_restores_original_suffixes(self) -> None:
        with _handler_with_aov_manager(
            outputPath="C:/baked",
            driver_suffixes=["AOVs", "AOVs_1"],
        ) as (handler, _, drivers):
            # Simulate render: filenameSuffix gets mutated, originals cached.
            handler._configure_renderer_output("cam_state_render0001", "C:/out", ".exr")
            assert drivers[0].filenameSuffix == "cam_state_render0001_AOVs"
            assert drivers[1].filenameSuffix == "cam_state_render0001_AOVs_1"

            # Patch parent's cleanup_render_elements so it doesn't try to do real work.
            with patch.object(
                DefaultMaxHandler,
                "cleanup_render_elements",
                lambda *args, **kwargs: None,
            ):
                handler.cleanup_render_elements({})

            assert drivers[0].filenameSuffix == "AOVs"
            assert drivers[1].filenameSuffix == "AOVs_1"
            # Cache cleared after restore
            assert handler._arnold_aov_driver_original_suffixes == []

    def test_cleanup_restores_original_output_path(self) -> None:
        """outputPath is mutated per frame and must be reverted at session end."""
        with _handler_with_aov_manager(
            outputPath="C:/Users/Artist/scene_outputs",
            driver_suffixes=["AOVs"],
        ) as (handler, aov_mgr, _):
            # Frame 0 overrides outputPath and caches the original once.
            handler._configure_renderer_output("cam_state_render0000", "C:/out", ".exr")
            assert aov_mgr.outputPath == "C:/out"
            # A later frame with a different dir must not re-capture the mutated value.
            handler._configure_renderer_output("cam_state_render0001", "C:/out2", ".exr")
            assert handler._arnold_aov_original_output_path == "C:/Users/Artist/scene_outputs"

            with patch.object(
                DefaultMaxHandler,
                "cleanup_render_elements",
                lambda *args, **kwargs: None,
            ):
                handler.cleanup_render_elements({})

            assert aov_mgr.outputPath == "C:/Users/Artist/scene_outputs"
            # Cache cleared after restore
            assert handler._arnold_aov_original_output_path is None

    def test_cleanup_no_op_when_nothing_was_cached(self) -> None:
        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["AOVs"]) as (
            handler,
            _,
            drivers,
        ):
            with patch.object(
                DefaultMaxHandler,
                "cleanup_render_elements",
                lambda *args, **kwargs: None,
            ):
                handler.cleanup_render_elements({})

            # Suffix unchanged because nothing was cached.
            assert drivers[0].filenameSuffix == "AOVs"

    def test_cleanup_runs_super_even_if_drivers_access_raises(self) -> None:
        """
        If reading aov_mgr.drivers raises during restore, the failure must not
        escape and skip the standard render-element cleanup (super()). The
        caches must still be cleared.
        """

        class _BoomDrivers:
            def __iter__(self):
                raise RuntimeError("pymxs drivers access boom")

        with _handler_with_aov_manager(outputPath="C:/baked", driver_suffixes=["AOVs"]) as (
            handler,
            aov_mgr,
            _,
        ):
            # Populate the caches with a normal frame first.
            handler._configure_renderer_output("frame_0", "C:/out", ".exr")
            # Now make the drivers access blow up during restore.
            aov_mgr.drivers = _BoomDrivers()

            super_called = {"value": False}

            def _fake_super(self, data):
                super_called["value"] = True

            with patch.object(DefaultMaxHandler, "cleanup_render_elements", _fake_super):
                # Must not raise despite the drivers access failing.
                handler.cleanup_render_elements({})

            assert super_called["value"] is True
            # Caches are cleared even though the driver restore failed.
            assert handler._arnold_aov_driver_original_suffixes == []
            assert handler._arnold_aov_original_output_path is None
