# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
# V-Ray Tile Merge Script
# Merges rendered tile regions into complete frames.
# V-Ray -region outputs full-size images (only region has pixels, rest is black).
# Uses Pillow for PNG/TIFF/JPG, OpenEXR+numpy for EXR.

import os
import re
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


def _find_tile_by_stat(output_dir, tile_index, base, frame, ext):
    """Locate a tile by stat-ing the two spellings tile_render.py can produce.

    Used when the output directory cannot be enumerated. ``os.listdir`` needs
    "List folder / Read data" on Windows while ``os.path.exists`` needs only
    "Traverse folder", and denying list while allowing traverse is a normal
    hardening configuration on shared render output volumes: artists can write
    and read their own frames but cannot enumerate the folder. Without this,
    every tile would be reported missing on such a share even though it rendered.

    Stat keeps the case-insensitivity of the filesystem, so only the tolerance
    for an unexpected padding width is lost relative to :func:`find_tile`.
    """
    padded = str(int(frame)).zfill(4)
    prefix = "_tile{}_{}".format(tile_index, base)
    for name in (
        "{}.{}{}".format(prefix, padded, ext),  # name as tile_render.py requests it
        "{}.{}.{}{}".format(prefix, padded, padded, ext),  # V-Ray re-numbered it
    ):
        candidate = os.path.join(output_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


def find_tile(output_dir, tile_index, base, frame, ext, names=None):
    """Locate a rendered tile, tolerating V-Ray's own frame numbering.

    ``tile_render.py`` asks V-Ray for ``_tile{N}_{base}.{frame}{ext}`` via
    ``-imgFile``, but that render also passes ``-frames``, which puts V-Ray in
    sequence mode. In that mode V-Ray inserts its own zero-padded frame number
    before the extension, so the file on disk is
    ``_tile{N}_{base}.{frame}.{frame}{ext}`` -- the frame appears twice. Other
    V-Ray builds/configurations have been observed writing the requested name
    verbatim instead.

    Matching is done with a digit-anchored regex rather than by building exact
    names: the padding width of the number V-Ray inserts comes from V-Ray and
    the scene's output settings, not from us, so hardcoding four digits would
    fail every tile if it were ever configured differently. ``0*`` before the
    frame accepts any width while staying anchored, so frame 1 still cannot pair
    with frame 10001.

    Requiring the optional second segment to be digits is what keeps the sibling
    channel outputs V-Ray writes for the same tile and frame out of the results
    (``_tile0_render.0021.Alpha.tif``, ``...diffuse.tif`` -- observed locally,
    where rendering to ``out.png`` also produced ``out.Alpha.png``). Merging one
    of those into the beauty pass would be a silently wrong image, which is a
    worse failure than the missing-tile error this function reports.

    ``base`` and ``ext`` are regex-escaped, so an output name containing
    metacharacters such as ``Scene[v2]`` is matched literally. Negative frames
    are supported, matching what ``zfill`` writes for them.

    ``names`` optionally supplies the directory contents. The output directory is
    shared by every tile of every frame, so its size grows with frames x tiles,
    and enumerating it once per tile would be quadratic -- costly on the network
    shares these outputs usually live on. ``main`` lists it once and passes the
    same snapshot for every tile; callers that omit it get a listing of their own.

    Returns the resolved path, or None when no tile for this frame is present.
    """
    prefix = "_tile{}_{}".format(tile_index, base)
    frame_number = int(frame)
    # The optional zeros sit inside the sign, because zfill pads after it:
    # str(-5).zfill(4) is "-005", so tile_render.py writes _tile0_name.-005.tif
    # for frame -5. A leading "0*" would require "-5" and never match that.
    # 3ds Max allows negative animation ranges and get_frames() passes
    # rt.animationrange.start straight through, so this is reachable without an
    # override. The second segment allows a sign for the same reason: V-Ray's own
    # number carries it, making the doubled form ".-005.-005.".
    frame_pattern = ("-" if frame_number < 0 else "") + r"0*" + str(abs(frame_number))
    # Case-insensitive to preserve the behaviour of the os.path.exists lookup this
    # replaced. That asked the filesystem, so on NTFS it resolved case-insensitively
    # and "_tile0_Render.0021.TIF" satisfied a lookup for "_tile0_render.0021.tif".
    # Matching os.listdir output would not. ext is the likeliest to diverge: the
    # submitter takes it from os.path.splitext(output_filename) while the name on
    # disk comes from V-Ray honouring the scene's output format. 3ds Max and V-Ray
    # are Windows-only, so this costs nothing.
    # The optional second segment is pinned to this same frame, not to digits in
    # general. V-Ray re-inserts the frame it rendered, so ".0021.0007." is not a
    # doubled name for frame 21 -- it is a stale file from another frame, and
    # accepting it would composite frame 7's pixels into frame 21's output. That
    # is the same silently-wrong-image failure the Alpha/diffuse exclusion above
    # exists to prevent, so it is closed the same way.
    pattern = re.compile(
        "^"
        + re.escape(prefix)
        + r"\."
        + frame_pattern
        + r"(\."
        + frame_pattern
        + r")?"
        + re.escape(ext)
        + "$",
        re.IGNORECASE,
    )

    if names is None:
        try:
            names = os.listdir(output_dir)
        except OSError:
            # Enumeration is a stricter permission than stat, so it can be denied
            # where the old os.path.exists lookup would have succeeded. Fall back
            # to that rather than reporting every tile missing. See
            # _find_tile_by_stat for the detail.
            return _find_tile_by_stat(output_dir, tile_index, base, frame, ext)

    # If a directory somehow holds more than one spelling for the same tile and
    # frame -- a stale file from a run with different output settings, say --
    # prefer the name we asked V-Ray for over the re-numbered one, then sort for
    # determinism. Never leave the choice to alphabetical order alone, which
    # would favour the doubled form ("0" sorts before the extension).
    matches = []
    for name in names:
        match = pattern.match(name)
        if match:
            matches.append((1 if match.group(1) else 0, name))

    if not matches:
        return None

    return os.path.join(output_dir, min(matches)[1])


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

    # Enumerate the output directory once and reuse the snapshot for every tile
    # and for the diagnostic below. The directory is shared by every tile of every
    # frame, so listing it per tile would scale with frames x tiles x tiles --
    # costly on the network shares these outputs usually live on.
    listing_error = None
    try:
        present = sorted(os.listdir(output_dir))
    except OSError as exc:
        present = []
        listing_error = exc
        # Passing names=None below routes every lookup through find_tile's stat
        # fallback, which still finds both spellings tile_render.py can produce.
        # Reported once here rather than per tile so the narrower matching is
        # visible in the task log.
        print(
            f"WARNING: could not list {output_dir}: {exc}. "
            "Falling back to exact-name lookup; tolerance for an unexpected "
            "frame padding width is unavailable."
        )

    # Resolve tile files. find_tile accepts the frame-numbering variants V-Ray
    # may produce, so a doubled frame number does not read as a missing tile.
    tile_paths = []
    missing = 0
    for row in range(total_rows):
        for col in range(total_cols):
            tile_index = row * total_cols + col
            tile_file = find_tile(
                output_dir,
                tile_index,
                base,
                frame,
                ext,
                names=None if listing_error is not None else present,
            )
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
        # the task log instead of requiring a separate investigation.
        #
        # Deliberately unfiltered: find_tile only fails when the name on disk is
        # not what we expect, and the prefix is one of the things that may have
        # diverged. Filtering on "_tile" would hide exactly those files and
        # report "Found 0 file(s)", which reads as "V-Ray wrote nothing" and
        # sends the investigation towards the render tasks instead of the naming.
        # Capped so one failing task cannot bury its own error in a shared output
        # directory holding every tile of every frame. Reuses the snapshot taken
        # above rather than enumerating a second time.
        if listing_error is not None:
            print(f"Could not list {output_dir}: {listing_error}")
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
