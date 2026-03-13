# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#!/usr/bin/env python3
# V-Ray Export + Path Fix Script
# Runs 3dsmaxcmd to export the vrscene, then replaces session-specific paths
# with original source paths so the render step's -remapPath works correctly.

import glob
import json
import os
import subprocess
import sys


def normalize_path(p):
    return p.replace("\\", "/")


def run_export():
    # Step 1: Run 3dsmaxcmd to export the vrscene
    maxcmd = r"{{Param.MaxCmdExecutable}}"
    scene_file = r"{{Param.SceneFile}}"
    export_script = r"{{Task.File.ExportScript}}"

    cmd = [maxcmd, scene_file, f"-script:{export_script}"]
    print("=== Running 3dsmaxcmd Export ===")
    print(f"  Command: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"ERROR: 3dsmaxcmd failed with exit code {result.returncode}")
        return result.returncode

    print("=== Export completed ===")
    return 0


def fix_vrscene_paths():
    # Step 2: Fix session paths in the exported vrscene
    rules_file = normalize_path(r"{{Session.PathMappingRulesFile}}")
    vrscene_path = normalize_path(r"{{Param.VRSceneOutputPath}}")

    print("=== Fix VRScene Paths ===")
    print(f"VRScene: {vrscene_path}")
    print(f"Rules file: {rules_file}")

    # Build reverse mapping: destination (session path) -> source (original path)
    reverse_map = {}
    if os.path.exists(rules_file):
        try:
            with open(rules_file, "r") as f:
                data = json.load(f)
                rules = data.get("path_mapping_rules", [])
                for rule in rules:
                    source = rule.get("source_path", "")
                    dest = rule.get("destination_path", "")
                    if source and dest:
                        # Replace dest paths with source paths in the vrscene
                        # Use both forward-slash and backslash variants
                        reverse_map[dest.replace("\\", "/")] = source.replace("\\", "/")
                        reverse_map[dest] = source
                        print(f"  Reverse map: {dest} -> {source}")
        except Exception as e:
            print(f"Warning: Failed to parse rules: {e}")
    else:
        print("No path mapping rules found, nothing to fix")
        return 0

    if not reverse_map:
        print("No mappings to reverse, nothing to fix")
        return 0

    # Find all vrscene files (could be multiple for per-frame export)
    vrscene_dir = os.path.dirname(vrscene_path)
    vrscene_base = os.path.splitext(os.path.basename(vrscene_path))[0]
    vrscene_files = glob.glob(os.path.join(vrscene_dir, vrscene_base + "*.vrscene"))

    if not vrscene_files:
        if os.path.exists(vrscene_path):
            vrscene_files = [vrscene_path]
        else:
            print(f"WARNING: No vrscene files found at {vrscene_path}")
            return 0

    for vrs_file in vrscene_files:
        print(f"Processing: {vrs_file}")
        try:
            with open(vrs_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            replacements = 0
            for session_path, original_path in reverse_map.items():
                count = content.count(session_path)
                if count > 0:
                    content = content.replace(session_path, original_path)
                    replacements += count
                    print(f"  Replaced {count} occurrences of session path")

            if replacements > 0:
                with open(vrs_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  Fixed {replacements} path(s) in {vrs_file}")
            else:
                print(f"  No session paths found in {vrs_file}")
        except Exception as e:
            print(f"  ERROR processing {vrs_file}: {e}")
            return 1

    print("=== Path fix complete ===")
    return 0


def main():
    rc = run_export()
    if rc != 0:
        return rc
    return fix_vrscene_paths()


if __name__ == "__main__":
    sys.exit(main())
