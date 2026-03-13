# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
# V-Ray Tile Render Script

import json
import os
import subprocess
import sys


def normalize_path(p):
    return p.replace("\\", "/")


def main():
    vray_cmd = normalize_path(r"{{Param.VRayExecutable}}")
    scene_file = normalize_path(r"{{Param.VRSceneOutputPath}}")
    output_dir = normalize_path(r"{{Param.OutputDir}}")
    output_filename = r"{{Param.OutputFileName}}"
    frame = r"{{Task.Param.Frame}}"
    image_width = int(r"{{Param.ImageWidth}}")
    image_height = int(r"{{Param.ImageHeight}}")
    total_cols = int(r"{{Param.RegionColumns}}")
    total_rows = int(r"{{Param.RegionRows}}")

    # Convert 1-based OpenJD params to 0-based
    col = int(r"{{Task.Param.RegionCol}}") - 1
    row = int(r"{{Task.Param.RegionRow}}") - 1

    print("=== Tile Render Task ===")
    print(f"Frame: {frame}, Col: {col}, Row: {row}")
    print(f"Image: {image_width}x{image_height}, Grid: {total_cols}x{total_rows}")

    # Pixel-based region coordinates (divmod, last tile gets remainder)
    delta_x, remainder_x = divmod(image_width, total_cols)
    delta_y, remainder_y = divmod(image_height, total_rows)
    x_start = delta_x * col
    x_end = delta_x * (col + 1)
    y_start = delta_y * row
    y_end = delta_y * (row + 1)
    if col == total_cols - 1:
        x_end += remainder_x
    if row == total_rows - 1:
        y_end += remainder_y

    print(f"Region: [{x_start},{y_start},{x_end},{y_end}]")

    # Tile output filename: _tile{N}_{base}.{frame}.{ext}
    tile_index = row * total_cols + col
    base, ext = os.path.splitext(output_filename)
    padded_frame = str(int(frame)).zfill(4)
    tile_filename = f"_tile{tile_index}_{base}.{padded_frame}{ext}"
    tile_filepath = os.path.join(output_dir, tile_filename)
    print(f"Output: {tile_filepath}")

    # Read path mapping rules
    rules_file = normalize_path(r"{{Session.PathMappingRulesFile}}")
    remap_args = []
    if os.path.exists(rules_file):
        try:
            with open(rules_file, "r") as f:
                data = json.load(f)
                rules = data.get("path_mapping_rules", [])
                print(f"Found {len(rules)} path mapping rule(s)")
                for rule in rules:
                    source = rule.get("source_path", "")
                    dest = rule.get("destination_path", "")
                    if source and dest:
                        remap_args.append(f"-remapPath={source}={dest}")
                        print(f"  Path mapping: {source} -> {dest}")
        except Exception as e:
            print(f"Warning: Failed to parse path mapping rules: {e}")

    # Build and execute V-Ray command
    region_str = f"{x_start};{y_start};{x_end};{y_end}"
    cmd = [
        vray_cmd,
        f"-sceneFile={scene_file}",
        f"-imgFile={tile_filepath}",
        f"-imgWidth={image_width}",
        f"-imgHeight={image_height}",
        f"-region={region_str}",
        f"-frames={frame}",
        "-display=0",
        *remap_args,
    ]

    print(f"\nExecuting V-Ray:\n  {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"ERROR: V-Ray failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        print(f"ERROR: V-Ray not found: {vray_cmd}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
