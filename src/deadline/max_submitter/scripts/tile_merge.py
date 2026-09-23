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

# How many filenames to print when a tile cannot be found. The output directory
# is shared by every tile of every frame, so an uncapped listing would bury the
# error it is meant to explain.
_MAX_LISTED_FILES = 50

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


def find_tile(output_dir, tile_index, base, frame, ext):
    """Locate a rendered tile, tolerating V-Ray's own frame numbering.

    ``tile_render.py`` asks V-Ray for ``_tile{N}_{base}.{frame}{ext}`` via
    ``-imgFile``, but that render also passes ``-frames``, which puts V-Ray in
    sequence mode. In that mode V-Ray inserts its own zero-padded frame number
    before the extension, so the file on disk is
    ``_tile{N}_{base}.{frame}.{frame}{ext}`` -- the frame appears twice. Other
    V-Ray builds/configurations have been observed writing the requested name
    verbatim instead. Both spellings are therefore checked, in that order.

    The two candidate names are built here, not searched for. The frame is padded
    with the same ``str(int(frame)).zfill(4)`` expression ``tile_render.py`` uses
    to build ``-imgFile``, so the two scripts cannot disagree about the name --
    which is exactly how the bug this fixes arose. It also means an unexpected
    padding width is a code change in both scripts rather than something resolved
    at runtime: V-Ray has only ever been observed writing four digits here.

    Naming the candidates rather than pattern-matching a directory listing is
    what the other Deadline Cloud tile implementations do: the V-Ray Linux sample
    job bundle builds the same expression in its render and merge scripts and
    tests it with ``[ -f ]``, the Cinema 4D adaptor resolves tiles through a
    single ``_tile_path`` helper shared by its save and assemble paths, and
    Deadline 10's DraftTileAssembler reads each tile's filename from its config
    file. It also keeps three failure modes out of this step: a lookup by name
    needs only "Traverse folder" on Windows where enumeration needs "List folder
    / Read data", it cannot be served a stale directory enumeration, and it
    cannot match a file we did not ask for -- notably the sibling channel outputs
    V-Ray writes for the same tile and frame (``_tile0_render.0021.Alpha.tif``,
    observed locally, where rendering to ``out.png`` also produced
    ``out.Alpha.png``). Compositing one of those into the beauty pass would be a
    silently wrong image, a worse failure than the missing-tile error reported by
    the caller.

    Negative frames work because the padding expression is shared: ``zfill`` pads
    after the sign, so frame -5 is ``-005`` on both sides. 3ds Max allows negative
    animation ranges and ``get_frames()`` passes ``rt.animationrange.start``
    straight through, so this is reachable without an override.

    Returns the resolved path, or None when neither spelling is present.
    """
    padded_frame = str(int(frame)).zfill(4)
    # The first candidate is written the same way tile_render.py builds -imgFile,
    #     tile_filename = f"_tile{tile_index}_{base}.{padded_frame}{ext}"
    # from a padded_frame computed by the same expression above, so the two are
    # identical character for character and a reviewer can see that they agree.
    # The second is that name with V-Ray's own frame number inserted.
    #
    # isfile rather than exists, so a directory carrying a tile's name is reported
    # missing here instead of failing later inside Pillow or OpenEXR, well away
    # from the cause. The V-Ray sample job bundle tests its tiles with [ -f ] for
    # the same reason.
    for name in (
        f"_tile{tile_index}_{base}.{padded_frame}{ext}",
        f"_tile{tile_index}_{base}.{padded_frame}.{padded_frame}{ext}",
    ):
        candidate = os.path.join(output_dir, name)
        if os.path.isfile(candidate):
            return candidate
    return None


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

    # Resolve tile files. find_tile checks both frame-numbering spellings V-Ray
    # may produce, so a doubled frame number does not read as a missing tile.
    tile_paths = []
    missing = 0
    for row in range(total_rows):
        for col in range(total_cols):
            tile_index = row * total_cols + col
            tile_file = find_tile(output_dir, tile_index, base, frame, ext)
            if tile_file is None:
                print(
                    f"ERROR: Missing tile {tile_index} for frame {padded_frame}: "
                    f"expected _tile{tile_index}_{base}.{padded_frame}{ext} or "
                    f"_tile{tile_index}_{base}.{padded_frame}.{padded_frame}{ext} "
                    f"in {output_dir}"
                )
                missing += 1
            else:
                tile_paths.append(tile_file)

    if missing > 0:
        print(f"ERROR: {missing} tile(s) missing")
        # List what is actually present so a naming mismatch is diagnosable from
        # the task log instead of requiring a separate investigation. Only on
        # failure, and best-effort: enumeration needs "List folder / Read data"
        # on Windows where the lookups above need only "Traverse folder", and
        # denying list while allowing traverse is a normal hardening
        # configuration on shared render output volumes. Losing the diagnostic
        # there is acceptable; failing the merge over it would not be.
        #
        # Deliberately unfiltered: find_tile only fails when the name on disk is
        # not what we expect, and the prefix is one of the things that may have
        # diverged. Filtering on "_tile" would hide exactly those files and
        # report "Found 0 file(s)", which reads as "V-Ray wrote nothing" and
        # sends the investigation towards the render tasks instead of the naming.
        # Capped so one failing task cannot bury its own error in a shared output
        # directory holding every tile of every frame.
        try:
            present = sorted(os.listdir(output_dir))
        except OSError as exc:
            print(f"Could not list {output_dir}: {exc}")
        else:
            print(f"Found {len(present)} file(s) in {output_dir}:")
            for name in present[:_MAX_LISTED_FILES]:
                print(f"  {name}")
            if len(present) > _MAX_LISTED_FILES:
                print(f"  ... and {len(present) - _MAX_LISTED_FILES} more")
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
