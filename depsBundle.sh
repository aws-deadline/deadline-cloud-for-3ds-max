#!/bin/bash
set -xeuo pipefail

python depsBundle.py

rm -f dependency_bundle/deadline_cloud_for_3ds_max_submitter-deps-windows.zip

cp dependency_bundle/deadline_cloud_for_3ds_max_submitter-deps.zip dependency_bundle/deadline_cloud_for_3ds_max_submitter-deps-windows.zip
