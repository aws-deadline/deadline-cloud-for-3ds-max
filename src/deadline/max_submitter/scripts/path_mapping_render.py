# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
# V-Ray Path Mapping Script
# Reads Deadline Cloud path mapping rules and executes V-Ray with -remapPath args.

import json
import subprocess
import os
import sys


def normalize_path(p):
    return p.replace("\\", "/")


def main():
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
    else:
        print(f"Warning: Path mapping rules file not found: {rules_file}")

    vray_cmd = normalize_path(r"{{Param.VRayExecutable}}")
    scene_file = normalize_path(r"{{Param.VRSceneOutputPath}}")
    output_dir = normalize_path(r"{{Param.OutputDir}}")
    output_filename = r"{{Param.OutputFileName}}"
    frame = r"{{Task.Param.Frame}}"

    if not os.path.exists(scene_file):
        print(f"ERROR: Scene file not found: {scene_file}")
        scene_dir = os.path.dirname(scene_file)
        if os.path.exists(scene_dir):
            print(f"Files in {scene_dir}:")
            for f_name in os.listdir(scene_dir):
                print(f"  {f_name}")
        return 1

    # Build output path — pad frame number into filename
    base, ext = os.path.splitext(output_filename)
    padded_frame = str(int(frame)).zfill(4)
    output_filepath = os.path.join(output_dir, f"{base}.{padded_frame}{ext}")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output: {output_filepath}")

    cmd = [
        vray_cmd,
        f"-sceneFile={scene_file}",
        f"-imgFile={output_filepath}",
        *remap_args,
        f"-frames={frame}",
        "-display=0",
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
