## 3ds Max Submitter

#### Manual installation

1. Copy `SMTDCMenuCreator.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`)
2. Put `DeadlineCloud-SubmitMaxToDeadlineCloud.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
3. Create a `python` folder in your scripts directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\scripts`).
4. Copy `dealine_cloud_max_submitter` folder into that newly created `python` folder.

#### Install for Development

1. Copy `SMTDCMenuCreator.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`).
2. Modify the file path in `SMTDCMenuCreator.ms`  to `<reporoot>/src/deadline/max_submitter`. Set the `DEBUG` variable to `true`.
3. Put `DeadlineCloud-SubmitMaxToDeadlineCloud.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
4. Modify the path in `DeadlineCloud-SubmitMaxToDeadlineCloud.mcr` to `<reporoot>/src/deadline/max_submitter/run_ui.py`. Set the `DEBUG` variable to `true`.
5. Install `deadline` package (from CodeArtifact) to `~\DeadlineCloudSubmitter\Submitters\3dsMax\python` using a Python 3.9 installation (for compatibility with Max)
    - `pip install deadline -t ~\DeadlineCloudSubmitter\Submitters\3dsMax\python`
    - TODO: optionally - we could provide a zip with all the packages for alpha/testing purposes.

### Usage

After installation a "Deadline Cloud" menu is available the menu bar. Run "Submit Max to Deadline Cloud" to open the submitter.
