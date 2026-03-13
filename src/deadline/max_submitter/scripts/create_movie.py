# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
# Create Movie Script
# Creates an MP4 movie from rendered frames using ffmpeg.

import os
import subprocess
import sys


def normalize_path(p):
    # Convert backslashes to forward slashes to avoid escape issues.
    return p.replace("\\", "/")


def main():
    create_movie = r"{{Param.CreateMovie}}"
    if create_movie != "true":
        print("Movie creation disabled, skipping")
        return 0

    output_dir = normalize_path(r"{{Param.OutputDir}}")
    output_filename = r"{{Param.OutputFileName}}"
    movie_filename = r"{{Param.MovieFilename}}"
    frame_rate = int(r"{{Param.FrameRate}}")

    base, ext = os.path.splitext(output_filename)

    # ffmpeg input pattern: base.%04d.ext
    input_pattern = os.path.join(output_dir, f"{base}.%04d{ext}")
    movie_path = os.path.join(output_dir, movie_filename)

    print("=== Create Movie ===")
    print(f"Input pattern: {input_pattern}")
    print(f"Output: {movie_path}")
    print(f"Frame rate: {frame_rate}")

    cmd = [
        "ffmpeg",
        "-framerate",
        str(frame_rate),
        "-i",
        input_pattern,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        movie_path,
    ]

    print(f"Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)
        print(f"Movie created: {movie_path}")
        return 0
    except FileNotFoundError:
        print("ERROR: ffmpeg not found. Cannot create movie.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"ERROR: ffmpeg failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
