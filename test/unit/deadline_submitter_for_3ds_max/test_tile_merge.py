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
    """Tile lookup must tolerate the frame-numbering variants V-Ray emits."""

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

    def test_output_name_containing_spaces(self, tmp_path):
        expected = _touch(tmp_path, "_tile3_Scene With Spaces.0021.0021.tif")
        found = find_tile(str(tmp_path), 3, "Scene With Spaces", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_single_numbering_preferred_over_doubled(self, tmp_path):
        exact = _touch(tmp_path, "_tile0_render.0021.tif")
        _touch(tmp_path, "_tile0_render.0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert os.path.samefile(found, exact)

    @pytest.mark.parametrize(
        "on_disk",
        [
            "_tile0_render.21.tif",  # no padding
            "_tile0_render.0021.tif",  # 4-digit, as tile_render.py requests
            "_tile0_render.00021.tif",  # 5-digit
            "_tile0_render.21.21.tif",  # doubled, no padding
            "_tile0_render.0021.0021.tif",  # doubled, 4-digit
            "_tile0_render.00021.00021.tif",  # doubled, 5-digit
        ],
    )
    def test_any_padding_width_resolves(self, tmp_path, on_disk):
        """The padding of the number V-Ray inserts comes from V-Ray, not from us.

        Hardcoding four digits would fail every tile on a scene configured with
        a different width, even though the tiles rendered fine.
        """
        expected = _touch(tmp_path, on_disk)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_channel_output_is_never_returned(self, tmp_path):
        """V-Ray writes sibling channel passes alongside the beauty pass.

        Observed locally: rendering to "out.png" also produced "out.Alpha.png".
        Merging an alpha or diffuse pass into the final frame would be a
        silently wrong image, so these must never be selected -- not even when
        the beauty pass itself is absent. A non-numeric segment is what
        disqualifies them.
        """
        _touch(tmp_path, "_tile0_render.0021.Alpha.tif")
        _touch(tmp_path, "_tile0_render.0021.diffuse.tif")
        _touch(tmp_path, "_tile0_render.0021.RGB_color.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_frame_is_not_matched_as_a_substring(self, tmp_path):
        """Leading zeros are absorbed by 0*, which stays anchored to the start."""
        _touch(tmp_path, "_tile0_render.10021.tif")
        _touch(tmp_path, "_tile0_render.00211.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_extension_must_match_exactly(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.tiff")
        _touch(tmp_path, "_tile0_render.0021.png")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_regex_characters_in_output_name_are_literal(self, tmp_path):
        """A name like Scene.v2 must not let '.' act as a wildcard."""
        _touch(tmp_path, "_tile0_SceneXv2.0021.tif")
        assert find_tile(str(tmp_path), 0, "Scene.v2", "21", ".tif") is None

    def test_beauty_pass_chosen_when_channel_outputs_sit_beside_it(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.0021.tif")
        _touch(tmp_path, "_tile0_render.0021.0021.Alpha.tif")
        _touch(tmp_path, "_tile0_render.0021.0021.diffuse.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_glob_characters_in_output_name(self, tmp_path):
        """Names are matched literally, so glob metacharacters are harmless."""
        expected = _touch(tmp_path, "_tile0_Scene[v2].0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "Scene[v2]", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_missing_tile_returns_none(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0022.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_does_not_match_a_different_frame(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0121.tif")
        _touch(tmp_path, "_tile0_render.0210.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_frame_1_does_not_match_frame_10001(self, tmp_path):
        # Substring matching would wrongly pair "0001" with "10001".
        _touch(tmp_path, "_tile0_render.10001.tif")
        assert find_tile(str(tmp_path), 0, "render", "1", ".tif") is None

    def test_does_not_match_a_different_tile_index(self, tmp_path):
        _touch(tmp_path, "_tile10_render.0021.tif")
        assert find_tile(str(tmp_path), 1, "render", "21", ".tif") is None

    def test_exr_extension(self, tmp_path):
        expected = _touch(tmp_path, "_tile2_render.0007.0007.exr")
        found = find_tile(str(tmp_path), 2, "render", "7", ".exr")
        assert found is not None
        assert os.path.samefile(found, expected)

    @pytest.mark.parametrize("frame", ["1", "01", "0001"])
    def test_frame_accepted_in_any_spelling(self, tmp_path, frame):
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


class TestFindTileNegativeFrames:
    """3ds Max allows negative animation ranges.

    ``max_utils.get_frames()`` passes ``rt.animationrange.start`` straight
    through for an active-time-segment render, so a negative frame reaches here
    without any override. ``tile_render.py`` names the file with
    ``str(int(frame)).zfill(4)``, and zfill pads *after* the sign, so frame -5 is
    written as ``_tile0_render.-005.tif``.
    """

    @pytest.mark.parametrize(
        "on_disk",
        [
            "_tile0_render.-5.tif",  # no padding
            "_tile0_render.-005.tif",  # zfill(4), as tile_render.py writes it
            "_tile0_render.-00005.tif",  # wider padding
            "_tile0_render.-005.-005.tif",  # doubled, the form V-Ray produces
            "_tile0_render.-5.-5.tif",  # doubled, unpadded
        ],
    )
    def test_negative_frame_resolves(self, tmp_path, on_disk):
        expected = _touch(tmp_path, on_disk)
        found = find_tile(str(tmp_path), 0, "render", "-5", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_negative_frame_does_not_match_its_positive_counterpart(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0005.tif")
        assert find_tile(str(tmp_path), 0, "render", "-5", ".tif") is None

    def test_positive_frame_does_not_match_its_negative_counterpart(self, tmp_path):
        _touch(tmp_path, "_tile0_render.-005.tif")
        assert find_tile(str(tmp_path), 0, "render", "5", ".tif") is None

    def test_negative_frame_excludes_channel_outputs(self, tmp_path):
        _touch(tmp_path, "_tile0_render.-005.Alpha.tif")
        assert find_tile(str(tmp_path), 0, "render", "-5", ".tif") is None

    def test_negative_frame_is_not_matched_as_a_substring(self, tmp_path):
        _touch(tmp_path, "_tile0_render.-0051.tif")
        assert find_tile(str(tmp_path), 0, "render", "-5", ".tif") is None

    def test_frame_zero_resolves(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0000.tif")
        found = find_tile(str(tmp_path), 0, "render", "0", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)


class TestFindTileCaseInsensitivity:
    """Matching is case-insensitive, as the os.path.exists lookup it replaced was.

    That lookup asked the filesystem, so on NTFS it resolved case-insensitively.
    Matching ``os.listdir`` output would not, and the extension is the likeliest
    to diverge: the submitter takes it from ``os.path.splitext(output_filename)``
    while the name on disk comes from V-Ray honouring the scene's output format.
    3ds Max and V-Ray are Windows-only.
    """

    @pytest.mark.parametrize(
        "on_disk",
        [
            "_tile0_render.0021.TIF",  # extension differs in case
            "_tile0_Render.0021.tif",  # output name differs in case
            "_tile0_RENDER.0021.TIF",  # both differ
            "_TILE0_render.0021.tif",  # the tile prefix differs
            "_tile0_Render.0021.0021.TIF",  # doubled, both differ
        ],
    )
    def test_case_differences_still_resolve(self, tmp_path, on_disk):
        expected = _touch(tmp_path, on_disk)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_case_insensitivity_does_not_admit_channel_outputs(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.ALPHA.TIF")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_case_insensitivity_does_not_admit_a_different_extension(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.TIFF")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_tie_break_does_not_depend_on_listing_order(self, tmp_path):
        """The selection must be stable regardless of the order names arrive in.

        Asserted against a synthetic snapshot rather than files on disk: two
        names differing only in case cannot co-exist on a case-insensitive
        filesystem, and this code is Windows-only, so creating them would leave
        one directory entry and the tie would never be exercised. Passing
        ``names`` pins the invariant the ``min(matches)`` tie-break relies on
        without depending on filesystem case behaviour.
        """
        names = ["_tile0_render.0021.tif", "_tile0_Render.0021.TIF"]
        first = find_tile(str(tmp_path), 0, "render", "21", ".tif", names=names)
        second = find_tile(str(tmp_path), 0, "render", "21", ".tif", names=list(reversed(names)))
        assert first == second

    def test_single_form_preferred_over_doubled_regardless_of_listing_order(self, tmp_path):
        """The requested spelling wins even when the doubled form is listed first."""
        names = ["_tile0_render.0021.0021.tif", "_tile0_RENDER.0021.TIF"]
        for candidate_order in (names, list(reversed(names))):
            found = find_tile(str(tmp_path), 0, "render", "21", ".tif", names=candidate_order)
            assert found is not None
            assert os.path.basename(found) == "_tile0_RENDER.0021.TIF"

    def test_single_form_still_preferred_over_doubled_regardless_of_case(self, tmp_path):
        exact = _touch(tmp_path, "_tile0_RENDER.0021.TIF")
        _touch(tmp_path, "_tile0_render.0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert os.path.samefile(found, exact)


class TestFindTileSecondSegmentIsTheSameFrame:
    """The doubled segment must be *this* frame, not any digits.

    V-Ray re-inserts the frame it rendered, so ".0021.0007." is not a doubled
    name for frame 21 -- it is a leftover from another frame. Accepting it would
    composite the wrong frame's pixels with no error, the same failure mode the
    Alpha/diffuse exclusion exists to prevent.
    """

    def test_mismatched_second_segment_is_rejected(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.0007.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_mismatched_second_segment_rejected_even_as_the_only_candidate(self, tmp_path):
        """With no tie to break, a stale file would otherwise be returned."""
        _touch(tmp_path, "_tile0_render.0021.0001.tif")
        _touch(tmp_path, "_tile1_render.0021.0001.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_matching_second_segment_still_resolves(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_second_segment_may_use_a_different_padding_width(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.21.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_negative_frame_mismatched_second_segment_is_rejected(self, tmp_path):
        _touch(tmp_path, "_tile0_render.-005.-007.tif")
        assert find_tile(str(tmp_path), 0, "render", "-5", ".tif") is None

    def test_stale_frame_is_not_picked_up_when_this_frame_is_absent(self, tmp_path):
        """The whole point: report missing rather than merge another frame."""
        for other in ("0001", "0007", "0100"):
            _touch(tmp_path, f"_tile0_render.0021.{other}.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None


class TestFindTileAcceptsAPreListedSnapshot:
    """``main`` enumerates the output directory once and reuses the snapshot.

    The directory is shared by every tile of every frame, so listing it per tile
    would scale with frames x tiles x tiles -- expensive on the network shares
    these outputs usually live on.
    """

    def test_names_are_used_instead_of_listing_the_directory(self, tmp_path):
        """A snapshot naming a file that is not on disk is still matched.

        Proves the lookup consults ``names`` rather than the filesystem.
        """
        found = find_tile(
            str(tmp_path), 0, "render", "21", ".tif", names=["_tile0_render.0021.0021.tif"]
        )
        assert found == os.path.join(str(tmp_path), "_tile0_render.0021.0021.tif")

    def test_snapshot_result_matches_listing_result(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.0021.tif")
        from_listing = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        from_snapshot = find_tile(
            str(tmp_path), 0, "render", "21", ".tif", names=sorted(os.listdir(str(tmp_path)))
        )
        assert from_listing == from_snapshot

    def test_empty_snapshot_reports_missing(self, tmp_path):
        _touch(tmp_path, "_tile0_render.0021.0021.tif")
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif", names=[]) is None

    def test_omitting_names_still_lists_the_directory(self, tmp_path):
        expected = _touch(tmp_path, "_tile0_render.0021.0021.tif")
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_unreadable_directory_without_names_returns_none(self, tmp_path):
        missing_dir = os.path.join(str(tmp_path), "does-not-exist")
        assert find_tile(missing_dir, 0, "render", "21", ".tif") is None


class TestFindTileWhenEnumerationIsDenied:
    """Enumeration is a stricter permission than stat, so it can be unavailable.

    ``os.listdir`` needs "List folder / Read data" on Windows while
    ``os.path.exists`` needs only "Traverse folder". Denying list while allowing
    traverse is a normal hardening configuration on shared render output volumes,
    and the previous exact-name lookup worked under it. Without a fallback every
    tile would be reported missing for tiles that rendered fine, regardless of
    how V-Ray named anything.
    """

    def _deny_listing(self, monkeypatch):
        def boom(_path):
            raise PermissionError(13, "Access is denied")

        monkeypatch.setattr(os, "listdir", boom)

    def test_requested_spelling_is_still_found(self, tmp_path, monkeypatch):
        expected = _touch(tmp_path, "_tile0_render.0021.tif")
        self._deny_listing(monkeypatch)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_doubled_spelling_is_still_found(self, tmp_path, monkeypatch):
        expected = _touch(tmp_path, "_tile0_render.0021.0021.tif")
        self._deny_listing(monkeypatch)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_negative_frame_is_still_found(self, tmp_path, monkeypatch):
        expected = _touch(tmp_path, "_tile0_render.-005.tif")
        self._deny_listing(monkeypatch)
        found = find_tile(str(tmp_path), 0, "render", "-5", ".tif")
        assert found is not None
        assert os.path.samefile(found, expected)

    def test_absent_tile_still_reports_missing(self, tmp_path, monkeypatch):
        self._deny_listing(monkeypatch)
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_channel_output_is_not_substituted(self, tmp_path, monkeypatch):
        """The fallback matches exact names, so siblings cannot be selected."""
        _touch(tmp_path, "_tile0_render.0021.Alpha.tif")
        self._deny_listing(monkeypatch)
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_unexpected_padding_is_not_found_by_the_fallback(self, tmp_path, monkeypatch):
        """Documents the one tolerance lost when enumeration is unavailable."""
        _touch(tmp_path, "_tile0_render.21.tif")
        self._deny_listing(monkeypatch)
        assert find_tile(str(tmp_path), 0, "render", "21", ".tif") is None

    def test_supplied_names_are_still_honoured(self, tmp_path, monkeypatch):
        """A caller-provided snapshot must not trigger a listing at all."""
        self._deny_listing(monkeypatch)
        found = find_tile(str(tmp_path), 0, "render", "21", ".tif", names=["_tile0_render.21.tif"])
        assert found == os.path.join(str(tmp_path), "_tile0_render.21.tif")
