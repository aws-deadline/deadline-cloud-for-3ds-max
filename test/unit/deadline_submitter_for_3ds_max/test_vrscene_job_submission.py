# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for vrscene_job_submission pure-logic functions."""

import pytest

from deadline.max_submitter.utilities.vrscene_job_submission import (
    calculate_region_coordinates,
    get_frame_range_from_string,
)


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
