# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for tile_merge tile discovery.

``tile_merge.py`` is an embedded task script whose ``main()`` is full of
``{{Param.X}}`` placeholders, so only the pure helper is imported here.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).parents[3] / "src" / "deadline" / "max_submitter" / "scripts" / "tile_merge.py"
)


def _load_tile_merge():
    """Load tile_merge.py without letting its import-time side effects escape.

    At import time the script prepends a temp pip-install directory to
    ``sys.path`` so ``ensure_package`` can install Pillow/numpy/OpenEXR on a
    worker. If that entry survived this import it would sit ahead of the venv
    for every test collected afterwards, so any later test importing PIL or
    numpy could silently resolve a stale copy left in tmp by a previous real
    tile merge -- an order- and host-dependent failure with nothing pointing
    back here. Snapshot and restore ``sys.path`` around the exec to contain it.
    """
    spec = importlib.util.spec_from_file_location("tile_merge_under_test", str(_SCRIPT))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = saved_path
    return module


tile_merge = _load_tile_merge()
find_tile = tile_merge.find_tile


def _touch(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_bytes(b"")
    return path


class TestFindTile:
    """Tile lookup must accept both frame-numbering spellings V-Ray emits."""

    def test_name_exactly_as_requested(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_doubled_frame_number(self, tmp_path):
        # What V-Ray actually writes when -imgFile carries a frame token and
        # -frames puts it in sequence mode: the frame number appears twice,
        # e.g. "_tile1_<output name>.0021.0021.tif".
        expected = _touch(tmp_path, "_tile1_render.0021.0021.tif")
        found = find_tile(str(tmp_path), 1, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_requested_name_preferred_over_doubled(self, tmp_path):
        """Candidates are checked in order, so the name we asked for wins.

        Both spellings can sit in one directory after a re-render onto a fleet
        whose V-Ray numbers frames differently. The order is fixed so the choice
        is deterministic rather than dependent on directory contents.
        """
        exact = _touch(tmp_path, "_tile0_render.0021.tif")
        _touch(tmp_path, "_tile0_render.0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert os.path.samefile(found, exact)

    def test_output_name_containing_spaces(self, tmp_path):
        expected = _touch(tmp_path, "_tile3_Scene With Spaces.0021.0021.tif")
        found = find_tile(str(tmp_path), 3, "Scene With Spaces", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_output_name_containing_metacharacters(self, tmp_path):
        """Names are used literally, so glob and regex metacharacters are inert."""
        expected = _touch(tmp_path, "_tile0_Scene[v2].0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "Scene[v2]", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_dot_in_output_name_is_not_a_wildcard(self, tmp_path):
        _touch(tmp_path, "_tile0_SceneXv2.0021.tif")
        assert find_tile(str(tmp_path), 0, "Scene.v2", "21", ".tif") is None

    def test_channel_output_is_never_returned(self, tmp_path):
        """V-Ray writes sibling channel passes alongside the beauty pass.

        Observed locally: rendering to "out.png" also produced "out.Alpha.png".
        Merging an alpha or diffuse pass into the final frame would be a
        silently wrong image, so these must never be selected -- not even when
        the beauty pass itself is absent.
        """
        _touch(tmp_path, "_tile0_render.0021.Alpha.tif")
        _touch(tmp_path, "_tile0_render.0021.diffuse.tif")
        _touch(tmp_path, "_tile0_render.0021.RGB_color.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_does_not_match_a_different_frame(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0121.tif")
        _touch(tmp_path, "_tile0_render.0210.tif")
        _touch(tmp_path, "_tile0_render.0022.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_doubled_segment_must_be_the_same_frame(self, tmp_path):
        """ ".0021.0007." is a leftover from another frame, not a doubled name.

        Accepting it would composite frame 7's pixels into frame 21's output with
        no error, the same silently-wrong-image failure the channel-output case
        guards against.
        """
        _touch(tmp_path, "_tile0_render.0021.0007.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_frame_1_does_not_match_frame_10001(self, tmp_path):
        _touch(tmp_path, "_tile0_render.10001.tif")
        assert find_tile(str(tmp_path), 0, "render", "1", ".tif") is None

    def test_does_not_match_a_different_tile_index(self, tmp_path):
        _touch(tmp_path, "_tile10_render.0021.tif")
        assert find_tile(str(tmp_path), 1, "render", "21", ".tif") is None

    def test_extension_must_match(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.tiff")
        _touch(tmp_path, "_tile0_render.0021.png")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_missing_tile_returns_none(self, tmp_path):
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_unreadable_directory_returns_none(self, tmp_path):
        missing_dir = os.path.join(str(tmp_path), "does-not-exist")
        assert find_tile(missing_dir, 0, "render", "21", ".tif") is None

    def test_a_directory_with_the_tile_name_is_not_a_tile(self, tmp_path):
        """Reported missing here rather than failing later inside Pillow."""
        (tmp_path / "_tile0_render.0021.tif").mkdir()
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_exr_extension(self, tmp_path):
        expected = _touch(tmp_path, "_tile2_render.0007.0007.exr")
        found = find_tile(str(tmp_path), 2, "render", "7", ".exr")
        assert found is not None
        assert os.path.samefile(found, expected)

    @pytest.mark.parametrize("frame", ["1", "01", "0001"])
    def test_frame_accepted_in_any_spelling(self, tmp_path, frame):
        """int(frame) normalises the task parameter before padding."""
        expected = _touch(tmp_path, "_tile0_render.0001.0001.tif")
        found = find_tile(str(tmp_path), 0, "render", frame, ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_all_four_tiles_of_a_2x2_grid_resolve(self, tmp_path):
        for index in range(4):
            _touch(tmp_path, f"_tile{index}_Scene With Spaces.0021.0021.tif")
        resolved = [
            find_tile(str(tmp_path), index, "Scene With Spaces", "21", ".tif") for index in range(4)
        ]
        assert all(path is not None for path in resolved)
        assert len(set(resolved)) == 4

    def test_lookup_does_not_enumerate_the_directory(self, tmp_path, monkeypatch):
        """Resolution must not depend on being able to list the directory.

        ``os.listdir`` needs "List folder / Read data" on Windows while
        ``os.path.exists`` needs only "Traverse folder". Denying list while
        allowing traverse is a normal hardening configuration on shared render
        output volumes, so a lookup that enumerated would report every tile
        missing there even though the tiles rendered fine.
        """

        def boom(_path):
            raise AssertionError("find_tile must not enumerate the output directory")

        expected = _touch(tmp_path, "_tile0_render.0021.0021.tif")
        monkeypatch.setattr(os, "listdir", boom)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)


class TestFindTileNegativeFrames:
    """3ds Max allows negative animation ranges.

    ``max_utils.get_frames()`` passes ``rt.animationrange.start`` straight
    through for an active-time-segment render, so a negative frame reaches here
    without any override. Both scripts pad with ``str(int(frame)).zfill(4)``, and
    zfill pads *after* the sign, so frame -5 is ``_tile0_render.-005.tif``.
    """

    def test_negative_frame_resolves(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.-005.tif")
        found = find_tile(str(tmp_path), 0, "render", "-5", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_negative_frame_doubled_resolves(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.-005.-005.tif")
        found = find_tile(str(tmp_path), 0, "render", "-5", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_negative_frame_does_not_match_its_positive_counterpart(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0005.tif")
        assert find_tile(str(tmp_path), 0, "render", "-5", ".tif") is None

    def test_positive_frame_does_not_match_its_negative_counterpart(self, tmp_path):
        _touch(tmp_path, "_tile0_render.-005.tif")
        assert find_tile(str(tmp_path), 0, "render", "5", ".tif") is None

    def test_frame_zero_resolves(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0000.tif")
        found = find_tile(str(tmp_path), 0, "render", "0", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)


class TestPaddingMatchesTheRenderScript:
    """The padding is a shared convention, not something resolved at runtime.

    ``tile_render.py`` builds ``-imgFile`` with ``str(int(frame)).zfill(4)``. This
    module uses the identical expression, which is what stops the two halves
    drifting apart -- the drift that caused the bug being fixed. A width V-Ray
    was never observed writing is deliberately not accepted; it would be a change
    in both scripts.
    """

    @pytest.mark.parametrize(
        "on_disk",
        [
            "_tile0_render.21.tif",  # unpadded
            "_tile0_render.00021.tif",  # five digits
            "_tile0_render.0021.21.tif",  # doubled, second segment unpadded
        ],
    )
    def test_other_padding_widths_are_not_accepted(self, tmp_path, on_disk):
        _touch(tmp_path, on_disk)
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_four_digit_padding_is_what_both_scripts_use(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)


class TestModuleLoadIsolation:
    """Loading tile_merge.py must not leak its sys.path mutation.

    The script prepends a temp pip-install directory to ``sys.path`` when
    imported. Left in place, that directory would precede the venv for every
    test collected after this file, so a later test importing PIL or numpy could
    resolve a stale copy installed there by a previous real tile merge.
    """

    def test_pip_target_is_not_left_on_sys_path(self):
        assert not any(
            "deadline_pip_packages" in entry for entry in sys.path
        ), "tile_merge.py's temp pip-install directory leaked onto sys.path"

    def test_reloading_restores_sys_path(self):
        before = list(sys.path)
        _load_tile_merge()
        assert sys.path == before

    def test_loaded_module_is_usable(self):
        """Isolation must not come at the cost of the module working."""
        assert callable(_load_tile_merge().find_tile)
