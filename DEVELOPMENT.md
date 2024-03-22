## 3ds Max Submitter

#### Manual installation

1. Copy `STDCMenuCreator.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`)
2. Put `AWSDeadline-SubmitToDeadlineCloud.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
3. Create a `python` folder in your scripts directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\scripts`).
4. Copy `max_submitter` folder into that newly created `python` folder.
5. Install `deadline` package (from CodeArtifact) to `~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts` using a Python 3.9 installation (for compatibility with Max)
    - `pip install deadline -t ~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts`

#### Install for Development

1. Copy `STDCMenuCreator.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`).
2. Modify the file path in `STDCMenuCreator.ms`  to `<reporoot>/src/deadline/max_submitter`. Set the `DEBUG` variable to `true`.
3. Put `AWSDeadline-SubmitToDeadlineCloud.mcr` and `AWSDeadline-RunJobBundleTests.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
4. Modify the path in `AWSDeadline-SubmitToDeadlineCloud.mcr` to `<reporoot>/src/deadline/max_submitter/run_ui.py`. Set the `DEBUG` variable to `true`.
5. Modify the path in `AWSDeadline-RunJobBundleTests.mcr` to `<reporoot>/src/deadline/max_submitter/job_bundle_output_test_runner.py`. Set the `DEBUG` variable to `true`.
6. Install `deadline` package (from CodeArtifact) to `~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts` using a Python 3.9 installation (for compatibility with Max)
    - `pip install deadline -t ~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts`

### Usage

After installation a "Deadline Cloud" menu is available the menu bar. Run "Submit to Deadline Cloud" to open the submitter.
