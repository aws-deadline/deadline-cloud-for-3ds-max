# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
# V-Ray Tile Merge Script
# Merges rendered tile regions into complete frames.
# V-Ray -region outputs full-size images (only region has pixels, rest is black).
# Uses Pillow for PNG/TIFF/JPG, OpenEXR+numpy for EXR.

import os
import subprocess
import sys
import tempfile

# Create a known install directory for pip packages
_pip_target = os.path.join(tempfile.gettempdir(), "deadline_pip_packages")
os.makedirs(_pip_target, exist_ok=True)
if _pip_target not in sys.path:
    sys.path.insert(0, _pip_target)


def ensure_package(package_name, import_name=None):
    import importlib

    if import_name is None:
        import_name = package_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {package_name} to {_pip_target}...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--target", _pip_target, package_name],
            check=True,
        )
        importlib.invalidate_caches()
        __import__(import_name)
        print(f"Installed {package_name}")


def normalize_path(p):
    return p.replace("\\", "/")


def merge_tiles_pillow(tile_paths, grid_cols, grid_rows, image_width, image_height, output_path):
    from PIL import Image, ImageChops

    delta_x, remainder_x = divmod(image_width, grid_cols)
    delta_y, remainder_y = divmod(image_height, grid_rows)

    first_tile = Image.open(tile_paths[0])
    tile_is_fullsize = first_tile.size[0] == image_width and first_tile.size[1] == image_height
    mode = first_tile.mode
    first_tile.close()

    if tile_is_fullsize:
        print("  Full-size tiles — additive compositing")
    else:
        print("  Tile-sized tiles — offset pasting")

    canvas = Image.new(mode, (image_width, image_height))

    for row in range(grid_rows):
        for col in range(grid_cols):
            tile_index = row * grid_cols + col
            tile_img = Image.open(tile_paths[tile_index])

            if tile_is_fullsize:
                canvas = ImageChops.add(canvas, tile_img)
            else:
                canvas.paste(tile_img, (delta_x * col, delta_y * row))

            tile_img.close()

    canvas.save(output_path)
    print(f"Saved: {output_path}")


def merge_tiles_exr(tile_paths, grid_cols, grid_rows, image_width, image_height, output_path):
    import numpy as np
    import OpenEXR
    import Imath

    first_exr = OpenEXR.InputFile(tile_paths[0])
    header = first_exr.header()
    channels = list(header["channels"].keys())
    pixel_type = Imath.PixelType(Imath.PixelType.FLOAT)

    dw = header["dataWindow"]
    tile_w = dw.max.x - dw.min.x + 1
    tile_h = dw.max.y - dw.min.y + 1
    first_exr.close()

    tile_is_fullsize = tile_w == image_width and tile_h == image_height
    print(f"  EXR channels: {channels}")

    delta_x, remainder_x = divmod(image_width, grid_cols)
    delta_y, remainder_y = divmod(image_height, grid_rows)

    channel_data = {ch: np.zeros((image_height, image_width), dtype=np.float32) for ch in channels}

    for row in range(grid_rows):
        for col in range(grid_cols):
            tile_index = row * grid_cols + col
            exr_file = OpenEXR.InputFile(tile_paths[tile_index])
            exr_dw = exr_file.header()["dataWindow"]
            tw = exr_dw.max.x - exr_dw.min.x + 1
            th = exr_dw.max.y - exr_dw.min.y + 1

            if tile_is_fullsize:
                for ch in channels:
                    arr = np.frombuffer(exr_file.channel(ch, pixel_type), dtype=np.float32).reshape(
                        (th, tw)
                    )
                    channel_data[ch] += arr
            else:
                x_start = delta_x * col
                x_end = delta_x * (col + 1)
                y_start = delta_y * row
                y_end = delta_y * (row + 1)
                if col == grid_cols - 1:
                    x_end += remainder_x
                if row == grid_rows - 1:
                    y_end += remainder_y
                for ch in channels:
                    arr = np.frombuffer(exr_file.channel(ch, pixel_type), dtype=np.float32).reshape(
                        (th, tw)
                    )
                    channel_data[ch][y_start:y_end, x_start:x_end] = arr

            exr_file.close()

    out_header = OpenEXR.Header(image_width, image_height)
    out_header["channels"] = header["channels"]
    out_file = OpenEXR.OutputFile(output_path, out_header)
    out_file.writePixels({ch: channel_data[ch].tobytes() for ch in channels})
    out_file.close()
    print(f"Saved EXR: {output_path}")


def main():
    output_dir = normalize_path(r"{{Param.OutputDir}}")
    output_filename = r"{{Param.OutputFileName}}"
    frame = r"{{Task.Param.Frame}}"
    image_width = int(r"{{Param.ImageWidth}}")
    image_height = int(r"{{Param.ImageHeight}}")
    total_cols = int(r"{{Param.RegionColumns}}")
    total_rows = int(r"{{Param.RegionRows}}")

    base, ext = os.path.splitext(output_filename)
    padded_frame = str(int(frame)).zfill(4)
    is_exr = ext.lower() == ".exr"

    print("=== Merge Regions ===")
    print(f"Frame: {frame}, Grid: {total_cols}x{total_rows}, Image: {image_width}x{image_height}")

    if is_exr:
        ensure_package("numpy")
        ensure_package("OpenEXR")
    else:
        ensure_package("Pillow", "PIL")

    # Verify tile files exist
    tile_paths = []
    missing = 0
    for row in range(total_rows):
        for col in range(total_cols):
            tile_index = row * total_cols + col
            tile_file = os.path.join(output_dir, f"_tile{tile_index}_{base}.{padded_frame}{ext}")
            tile_paths.append(tile_file)
            if not os.path.exists(tile_file):
                print(f"ERROR: Missing tile: {tile_file}")
                missing += 1

    if missing > 0:
        print(f"ERROR: {missing} tile(s) missing")
        return 1

    final_output = os.path.join(output_dir, f"{base}.{padded_frame}{ext}")
    print(f"Merging {len(tile_paths)} tiles into: {final_output}")

    if is_exr:
        merge_tiles_exr(tile_paths, total_cols, total_rows, image_width, image_height, final_output)
    else:
        merge_tiles_pillow(
            tile_paths, total_cols, total_rows, image_width, image_height, final_output
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
