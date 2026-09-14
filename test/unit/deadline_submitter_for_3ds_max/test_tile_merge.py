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
_RENDER_SCRIPT = _SCRIPT.parent / "tile_render.py"


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
    """The tile name is built, not searched for."""

    def test_tile_is_found(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_output_name_containing_spaces(self, tmp_path):
        expected = _touch(tmp_path, "_tile3_Scene With Spaces.0021.tif")
        found = find_tile(str(tmp_path), 3, "Scene With Spaces", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_output_name_containing_metacharacters(self, tmp_path):
        """Names are used literally, so glob and regex metacharacters are inert."""
        expected = _touch(tmp_path, "_tile0_Scene[v2].0021.tif")
        found = find_tile(str(tmp_path), 0, "Scene[v2]", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_dot_in_output_name_is_not_a_wildcard(self, tmp_path):
        _touch(tmp_path, "_tile0_SceneXv2.0021.tif")
        assert find_tile(str(tmp_path), 0, "Scene.v2", "21", ".tif") is None

    def test_doubled_frame_number_is_not_accepted(self, tmp_path):
        """tile_render.py passes -noFrameNumbers=1, so this name cannot occur.

        If it ever does, V-Ray numbered the file despite the flag and the render
        side needs fixing -- reporting the tile missing surfaces that, where
        quietly accepting it would hide a regression in the render script.
        """
        _touch(tmp_path, "_tile0_render.0021.0021.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_channel_output_is_never_returned(self, tmp_path):
        """V-Ray writes sibling channel passes alongside the beauty pass.

        Observed locally: rendering to "out.png" also produced "out.Alpha.png".
        Merging an alpha or diffuse pass into the final frame would be a
        silently wrong image.
        """
        _touch(tmp_path, "_tile0_render.0021.Alpha.tif")
        _touch(tmp_path, "_tile0_render.0021.diffuse.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_does_not_match_a_different_frame(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0121.tif")
        _touch(tmp_path, "_tile0_render.0022.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

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
        expected = _touch(tmp_path, "_tile2_render.0007.exr")
        found = find_tile(str(tmp_path), 2, "render", "7", ".exr")
        assert found is not None
        assert os.path.samefile(found, expected)

    @pytest.mark.parametrize("frame", ["1", "01", "0001"])
    def test_frame_accepted_in_any_spelling(self, tmp_path, frame):
        """int(frame) normalises the task parameter before padding."""
        expected = _touch(tmp_path, "_tile0_render.0001.tif")
        found = find_tile(str(tmp_path), 0, "render", frame, ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_lookup_does_not_enumerate_the_directory(self, tmp_path, monkeypatch):
        """Resolution must not depend on being able to list the directory.

        ``os.listdir`` needs "List folder / Read data" on Windows while
        ``os.path.isfile`` needs only "Traverse folder". Denying list while
        allowing traverse is a normal hardening configuration on shared render
        output volumes.
        """

        def boom(_path):
            raise AssertionError("find_tile must not enumerate the output directory")

        expected = _touch(tmp_path, "_tile0_render.0021.tif")
        monkeypatch.setattr(os, "listdir", boom)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_all_four_tiles_of_a_2x2_grid_resolve(self, tmp_path):
        for index in range(4):
            _touch(tmp_path, f"_tile{index}_Scene With Spaces.0021.tif")
        resolved = [
            find_tile(str(tmp_path), index, "Scene With Spaces", "21", ".tif") for index in range(4)
        ]
        assert all(path is not None for path in resolved)
        assert len(set(resolved)) == 4


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


class TestRenderAndMergeAgreeOnTheName:
    """The two scripts must build the tile name identically.

    They disagreeing is the bug this change fixes, so it is worth pinning rather
    than trusting. Asserted against the text of tile_render.py so a future edit
    to either side has to touch this test.
    """

    def test_both_scripts_use_the_same_expression(self):
        render_src = _RENDER_SCRIPT.read_text(encoding="utf-8")
        merge_src = _SCRIPT.read_text(encoding="utf-8")
        expression = 'f"_tile{tile_index}_{base}.{padded_frame}{ext}"'
        assert expression in render_src, "tile_render.py no longer builds the name this way"
        assert expression in merge_src, "tile_merge.py no longer builds the name this way"

    def test_both_scripts_pad_the_frame_the_same_way(self):
        render_src = _RENDER_SCRIPT.read_text(encoding="utf-8")
        merge_src = _SCRIPT.read_text(encoding="utf-8")
        padding = "str(int(frame)).zfill(4)"
        assert padding in render_src
        assert padding in merge_src

    def test_render_script_disables_vray_frame_numbering(self):
        """Without this flag V-Ray appends its own number and the merge fails."""
        render_src = _RENDER_SCRIPT.read_text(encoding="utf-8")
        assert '"-noFrameNumbers=1"' in render_src


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
