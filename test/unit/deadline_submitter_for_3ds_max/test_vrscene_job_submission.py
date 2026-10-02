# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for vrscene_job_submission pure-logic functions."""

import pytest

# openjd-model is a TEST dependency only. The submitter does not import it: the
# frame list is handed to the service verbatim and OpenJD parses it there. It is
# used here to check our validator agrees with the parser that will actually
# judge the value, so the two cannot drift apart without a test failing.
from openjd.model import IntRangeExpr

from deadline.max_submitter.utilities.vrscene_job_submission import (
    calculate_region_coordinates,
    get_frame_range_from_string,
    parse_frame_groups,
    validate_frame_string,
)


def _openjd_accepts(frame_string: str) -> bool:
    """Whether OpenJD's own range parser accepts this value."""
    try:
        IntRangeExpr.from_str(frame_string)
        return True
    except Exception:
        return False


class TestCalculateRegionCoordinates:
    """Tests for pixel-based tile coordinate calculation."""

    def test_single_tile_covers_full_image(self):
        result = calculate_region_coordinates(0, 0, 1, 1, 1920, 1080)
        assert result == (0, 0, 1920, 1080)

    def test_2x2_grid_top_left(self):
        result = calculate_region_coordinates(0, 0, 2, 2, 1920, 1080)
        assert result == (0, 0, 960, 540)

    def test_2x2_grid_top_right(self):
        result = calculate_region_coordinates(1, 0, 2, 2, 1920, 1080)
        assert result == (960, 0, 1920, 540)

    def test_2x2_grid_bottom_left(self):
        result = calculate_region_coordinates(0, 1, 2, 2, 1920, 1080)
        assert result == (0, 540, 960, 1080)

    def test_2x2_grid_bottom_right(self):
        result = calculate_region_coordinates(1, 1, 2, 2, 1920, 1080)
        assert result == (960, 540, 1920, 1080)

    def test_remainder_pixels_go_to_last_column(self):
        # 1921 / 2 = 960 remainder 1 — last column gets the extra pixel
        result = calculate_region_coordinates(1, 0, 2, 1, 1921, 1080)
        assert result == (960, 0, 1921, 1080)

    def test_remainder_pixels_go_to_last_row(self):
        # 1081 / 2 = 540 remainder 1 — last row gets the extra pixel
        result = calculate_region_coordinates(0, 1, 1, 2, 1920, 1081)
        assert result == (0, 540, 1920, 1081)

    def test_remainder_pixels_both_axes(self):
        # 1921 / 3 = 640 r1, 1081 / 3 = 360 r1
        # Bottom-right tile (2,2) should get remainder on both axes
        result = calculate_region_coordinates(2, 2, 3, 3, 1921, 1081)
        assert result == (1280, 720, 1921, 1081)
        # Middle tile should NOT get remainder
        result_mid = calculate_region_coordinates(1, 1, 3, 3, 1921, 1081)
        assert result_mid == (640, 360, 1280, 720)

    def test_tiles_cover_full_image_no_gaps(self):
        """All tiles together should cover every pixel exactly once."""
        cols, rows, w, h = 3, 2, 1920, 1080
        covered = set()
        for r in range(rows):
            for c in range(cols):
                x0, y0, x1, y1 = calculate_region_coordinates(c, r, cols, rows, w, h)
                for x in range(x0, x1):
                    for y in range(y0, y1):
                        assert (x, y) not in covered, f"Pixel ({x},{y}) covered twice"
                        covered.add((x, y))
        assert len(covered) == w * h

    def test_3x3_grid_standard_hd(self):
        # 1920 / 3 = 640 exact, 1080 / 3 = 360 exact
        assert calculate_region_coordinates(0, 0, 3, 3, 1920, 1080) == (0, 0, 640, 360)
        assert calculate_region_coordinates(2, 2, 3, 3, 1920, 1080) == (1280, 720, 1920, 1080)

    # --- Error cases ---

    def test_zero_columns_raises(self):
        with pytest.raises(ValueError, match="at least 1x1"):
            calculate_region_coordinates(0, 0, 0, 1, 1920, 1080)

    def test_zero_rows_raises(self):
        with pytest.raises(ValueError, match="at least 1x1"):
            calculate_region_coordinates(0, 0, 1, 0, 1920, 1080)

    def test_column_out_of_bounds_raises(self):
        with pytest.raises(ValueError, match="out of bounds"):
            calculate_region_coordinates(2, 0, 2, 2, 1920, 1080)

    def test_row_out_of_bounds_raises(self):
        with pytest.raises(ValueError, match="out of bounds"):
            calculate_region_coordinates(0, 2, 2, 2, 1920, 1080)

    def test_negative_column_raises(self):
        with pytest.raises(ValueError, match="out of bounds"):
            calculate_region_coordinates(-1, 0, 2, 2, 1920, 1080)

    def test_zero_image_width_raises(self):
        with pytest.raises(ValueError, match="at least 1x1"):
            calculate_region_coordinates(0, 0, 1, 1, 0, 1080)

    def test_image_too_small_for_grid_raises(self):
        with pytest.raises(ValueError, match="too small"):
            calculate_region_coordinates(0, 0, 100, 1, 10, 10)


class TestGetFrameRangeFromString:
    """Tests for frame range string parsing."""

    def test_single_frame(self):
        assert get_frame_range_from_string("1") == (1, 1)

    def test_single_frame_with_whitespace(self):
        assert get_frame_range_from_string("  42  ") == (42, 42)

    def test_simple_range(self):
        assert get_frame_range_from_string("1-100") == (1, 100)

    def test_range_same_frame(self):
        assert get_frame_range_from_string("5-5") == (5, 5)

    def test_comma_separated(self):
        assert get_frame_range_from_string("1,5,10") == (1, 10)

    def test_comma_separated_unordered(self):
        assert get_frame_range_from_string("10,1,5") == (1, 10)

    def test_zero_frame(self):
        assert get_frame_range_from_string("0") == (0, 0)

    def test_large_range(self):
        assert get_frame_range_from_string("0-9999") == (0, 9999)

    def test_non_contiguous_returns_bounding_range(self):
        assert get_frame_range_from_string("1-10,20-30") == (1, 30)

    def test_descending_range_is_rejected_like_openjd(self):
        """OpenJD requires a negative step to count down, so "5-1" is an error.

        This is never reached with bad input in practice:
        validate_vrscene_export_settings runs first and refuses the submission
        with a message naming the problem. Raising here rather than guessing the
        artist meant "1-5" keeps this function honest about what it was given.
        """
        with pytest.raises(ValueError, match="negative step"):
            get_frame_range_from_string("5-1")

    def test_descending_range_with_negative_step_is_bounded(self):
        assert get_frame_range_from_string("10-1:-1") == (1, 10)

    def test_step_range_bounds(self):
        assert get_frame_range_from_string("1-100:5") == (1, 100)

    def test_negative_frames(self):
        assert get_frame_range_from_string("-10--5") == (-10, -5)

    def test_negative_and_positive_frames(self):
        assert get_frame_range_from_string("-5,0,5") == (-5, 5)

    def test_huge_span_is_not_expanded(self):
        """Bounds must be read from the endpoints, never by walking the span.

        This is called on the raw frame-list field before validation, so a typo
        such as an extra zero must not allocate the whole range in memory.
        Returning the right answer for a billion-frame span is the assertion:
        expanding it would exhaust memory rather than merely be slow, so no
        timing check is needed (and a wall-clock threshold would be flaky on a
        loaded CI runner).
        """
        assert get_frame_range_from_string("1-1000000000") == (1, 1000000000)

    def test_huge_non_contiguous_span_is_not_expanded(self):
        assert get_frame_range_from_string("1-500000000,900000000-1000000000") == (1, 1000000000)

    def test_mixed_singles_and_ranges_bounding(self):
        assert get_frame_range_from_string("1-5,50-55,100") == (1, 100)


class TestParseFrameGroups:
    """Each comma-separated group is reduced to its (low, high) span.

    Endpoints only, never the frames between them: this runs on the raw
    frame-list field, so expanding "1-100000000" would allocate a hundred
    million integers inside the 3ds Max process. A string-length limit does not
    help, because that value is eleven characters.
    """

    def test_single_frame(self):
        assert parse_frame_groups("5") == [(5, 5)]

    def test_range(self):
        assert parse_frame_groups("1-10") == [(1, 10)]

    def test_range_same_frame(self):
        assert parse_frame_groups("5-5") == [(5, 5)]

    def test_step_range(self):
        assert parse_frame_groups("1-10:2") == [(1, 10)]

    def test_descending_step_range(self):
        assert parse_frame_groups("10-1:-2") == [(1, 10)]

    def test_groups_keep_their_written_order(self):
        assert parse_frame_groups("21,1-3") == [(21, 21), (1, 3)]

    def test_gaps(self):
        assert parse_frame_groups("1-3,6,8") == [(1, 3), (6, 6), (8, 8)]

    def test_whitespace_tolerated(self):
        assert parse_frame_groups("  1 - 3 ,  6  ") == [(1, 3), (6, 6)]

    def test_zero_and_negative_frames(self):
        assert parse_frame_groups("0,-5,-10--7") == [(0, 0), (-5, -5), (-10, -7)]

    def test_huge_span_is_not_expanded(self):
        """Returning the right answer for a billion-frame span is the assertion.

        Expanding it would exhaust memory rather than merely be slow, so no
        timing check is needed -- and a wall-clock threshold would be flaky on a
        loaded CI runner.
        """
        assert parse_frame_groups("1-1000000000") == [(1, 1000000000)]

    @pytest.mark.parametrize(
        "bad",
        ["", "   ", "abc", "1-", "-", "1..5", "1;2", "1-2-3", "1,,2", "1-10:"],
    )
    def test_malformed_input_raises(self, bad):
        with pytest.raises(ValueError):
            parse_frame_groups(bad)

    def test_descending_without_step_raises(self):
        with pytest.raises(ValueError, match="negative step"):
            parse_frame_groups("5-1")

    def test_zero_step_raises(self):
        with pytest.raises(ValueError, match="step of zero"):
            parse_frame_groups("1-10:0")

    def test_ascending_range_with_negative_step_raises(self):
        with pytest.raises(ValueError, match="counts up"):
            parse_frame_groups("1-10:-2")

    def test_descending_range_with_positive_step_raises(self):
        with pytest.raises(ValueError, match="counts down"):
            parse_frame_groups("10-1:2")


class TestValidateFrameString:
    """Our validation must agree with OpenJD, which is what judges the value.

    The frame list is sent to the service verbatim as the Frames job parameter,
    so OpenJD's parser has the final say. These tests pin that we accept exactly
    what it accepts: being stricter would block legitimate jobs, being looser
    would let the service reject a submission we said was fine.
    """

    ACCEPTED = [
        "1",
        "0",
        "-5",
        "1-10",
        "1-1",
        "1,2,3",
        "1, 3, 5",
        "  1-5  ",
        "1-3,6,8",
        "1-10,12-17,21",
        "21,1-3",
        "8,6,1-3",
        "1-10:2",
        "1-10:3",
        "10-1:-2",
        "1-10:2,11-20:2",
        "-5--1",
    ]

    REJECTED = [
        "5-1",
        "1-5,3-7",
        "5,5,5",
        "1-5,5-9",
        "1-5,5",
        "1-10:2,2-10:2",
        "1-10:0",
        "",
        "abc",
        "1-",
        "1..5",
        "1;2",
        "1-2-3",
    ]

    @pytest.mark.parametrize("frame_string", ACCEPTED)
    def test_accepted(self, frame_string):
        assert validate_frame_string(frame_string) == []

    @pytest.mark.parametrize("frame_string", REJECTED)
    def test_rejected_with_a_message(self, frame_string):
        problems = validate_frame_string(frame_string)
        assert problems, f"expected {frame_string!r} to be reported"
        assert all(problem.strip() for problem in problems)

    @pytest.mark.parametrize("frame_string", ACCEPTED + REJECTED)
    def test_agrees_with_openjd(self, frame_string):
        """The property that matters: our verdict matches the real parser's."""
        assert (validate_frame_string(frame_string) == []) == _openjd_accepts(
            frame_string
        ), f"{frame_string!r}: validator and OpenJD disagree"

    def test_overlap_message_names_both_ranges(self):
        problems = validate_frame_string("1-5,3-7")
        assert len(problems) == 1
        assert "1-5" in problems[0] and "3-7" in problems[0]

    def test_duplicate_single_frame_is_reported(self):
        problems = validate_frame_string("5,5")
        assert problems and "5" in problems[0]

    def test_overlap_is_found_regardless_of_written_order(self):
        assert validate_frame_string("3-7,1-5") != []

    def test_gaps_are_not_overlaps(self):
        assert validate_frame_string("1-3,5-7,9") == []

    def test_adjacent_ranges_are_allowed(self):
        """1-5 and 6-10 touch but do not share a frame."""
        assert validate_frame_string("1-5,6-10") == []


class TestCreateVrsceneRenderJobParameters:
    """Tests for create_vrscene_render_job_parameters."""

    def _make_settings(self, render_engine=0, columns=1, rows=1):
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.vrscene_render_engine = render_engine
        settings.vrscene_render_region_columns = columns
        settings.vrscene_render_region_rows = rows
        return settings

    def test_render_engine_cpu_not_in_params(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings(render_engine=0)
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        names = [p["name"] for p in params]
        assert "RenderEngine" in names
        render_engine_param = next(p for p in params if p["name"] == "RenderEngine")
        assert render_engine_param["value"] == "0"

    def test_render_engine_cuda_in_params(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings(render_engine=5)
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        render_engine_param = next(p for p in params if p["name"] == "RenderEngine")
        assert render_engine_param["value"] == "5"

    def test_render_engine_rtx_in_params(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings(render_engine=7)
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        render_engine_param = next(p for p in params if p["name"] == "RenderEngine")
        assert render_engine_param["value"] == "7"

    def test_output_filename_respected(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings()
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.tiff", "1", "vray.exe"
        )
        output_param = next(p for p in params if p["name"] == "OutputFileName")
        assert output_param["value"] == "scene.tiff"

    def test_output_filename_not_hardcoded_png(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings()
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.exr", "1", "vray.exe"
        )
        output_param = next(p for p in params if p["name"] == "OutputFileName")
        assert output_param["value"] == "scene.exr"
        assert output_param["value"] != "scene.png"


class TestRTEngineParameters:
    """Tests for RT engine parameters in create_vrscene_render_job_parameters."""

    def _make_settings(self, render_engine=0, rt_timeout=0.0, rt_noise=0.001, rt_sample_level=0):
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.vrscene_render_engine = render_engine
        settings.vrscene_rt_timeout = rt_timeout
        settings.vrscene_rt_noise = rt_noise
        settings.vrscene_rt_sample_level = rt_sample_level
        settings.vrscene_render_region_columns = 1
        settings.vrscene_render_region_rows = 1
        return settings

    def _get_param(self, params, name):
        return next((p for p in params if p["name"] == name), None)

    def test_rt_timeout_in_params(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings(rt_timeout=5.0)
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        assert self._get_param(params, "RTTimeout")["value"] == "5.0"

    def test_rt_noise_in_params(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings(rt_noise=0.005)
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        assert self._get_param(params, "RTNoise")["value"] == "0.005"

    def test_rt_sample_level_in_params(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings(rt_sample_level=1000)
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        assert self._get_param(params, "RTSampleLevel")["value"] == "1000"

    def test_rt_defaults(self):
        from deadline.max_submitter.utilities.vrscene_job_submission import (
            create_vrscene_render_job_parameters,
        )

        settings = self._make_settings()
        params = create_vrscene_render_job_parameters(
            settings, "/scene.vrscene", "/output", "scene.png", "1", "vray.exe"
        )
        assert self._get_param(params, "RTTimeout")["value"] == "0.0"
        assert self._get_param(params, "RTNoise")["value"] == "0.001"
        assert self._get_param(params, "RTSampleLevel")["value"] == "0"
