[deadline-cloud-monitor-setup]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor
[aws-cli-credentials]: https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-authentication.html
[3ds-max-2024-folders-documentation]: https://help.autodesk.com/view/MAXDEV/2024/ENU/?guid=GUID-F7577416-051E-478C-BB5D-81243BAAC8EC

# Development documentation
This package has two active branches:

- `mainline` -- For active development. This branch is not intended to be consumed by other packages. Any commit to this branch may break APIs, dependencies, and so on, and thus break any consumer without notice.
- `release` -- The official release of the package intended for consumers. Any breaking releases will be accompanied with an increase to this package's interface version.

## Build / Test / Release

### Build the package

```bash
hatch build
```

### Run tests

```bash
hatch run test
```

### Run linting

```bash
hatch run lint
```

### Run formatting

```bash
hatch run fmt
```

### Run tests for all supported Python versions

```bash
hatch run all:test
```

## Submitter Development Workflow

WARNING: This workflow installs additional Python packages into your 3ds Max's python distribution.

#### Installer installation (Recommended)
1. Download the install builder tool from https://installbuilder.com/ (Evaluation)
1. Clone `deadline-cloud-for-3ds-max`, and build your local copy running `hatch build`.
1. Run hatch build
1. Run - `hatch run installer:build-installer --local-dev`
1. Installer should be built under the `installer` sub-folder.
1. Double click on the built installer to setup all 3dsMax versions.

##### Quick Update for development.
1. After using the Installer installation, developers can quickly iterate by using `.\scripts\update_installed_files.bat` The script will copy and update all `.py` files.

#### Manual installation

1. Clone `deadline-cloud-for-3ds-max`, and build your local copy running `hatch build`.
1. To install the submitter in 3dsMax, you need to copy the UI components into the corresponding 3ds Max installation directories. You can find the UI component files in your local copy of `deadline-cloud-for-3ds-max`.
    1. Copy `<LOCAL_REPO_PATH>\install_files\DeadlineCloudMenu.ms` into your 3DS Max startup scripts (e.g. `C:\Program Files\Autodesk\<version>\scripts\Startup`, more details about 3ds Max system directories can be found in the 3ds Max [documentation][3ds-max-2024-folders-documentation]).
    1. Copy `<LOCAL_REPO_PATH>\install_files\AWSDeadline-SubmitToDeadlineCloud.mcr` in 3ds Max usermacros directory (e.g. `C:\Users\<username>\AppData\Local\Autodesk\3dsMax\<version>\ENU\usermacros`).
1. The point of entry for the submitter is the `run_ui.py` file under the `max_submitter` folder. Thus, this file needs to be discoverable by 3dsMax, and `max_submitter` needs to be a discoverable package by python. In Powershell run:
    1. `$env:ADSK_3DSMAX_SCRIPTS_ADDON_DIR += ";<LOCAL_REPO_PATH>\src\deadline\max_submitter"`.
    1. `$env:PYTHONPATH += ";<LOCAL_REPO_PATH>\src\;<LOCAL_REPO_PATH>\src\deadline\max_submitter"`.
1. Install `deadline` package to `~\DeadlineCloudSubmitter\Submitters\3dsMax\scripts`, using a python version that is compatible with the version of 3dsMax that you are using. In Powershell run:
    1. `& "C:\Program Files\Autodesk\<version>\Python\python.exe" -m ensurepip`
    1. `& "C:\Program Files\Autodesk\<version>\Python\python.exe" -m pip install deadline -t $env:HOMEPATH\DeadlineCloudSubmitter\Submitters\3dsMax\scripts` 
1. Run `3dsmax` from the same command-line window where the environment variables were set. To do so, `3dsmax` needs to be part of the PATH. In Powershell run `$env:PATH += ";C:\Program Files\Autodesk\<version>"`.
1. To supply AWS account credentials for the submitter to use when submitting a job you can either:
    1. [Install and set up the Deadline Cloud Monitor][deadline-cloud-monitor-setup], and then log in to the monitor. Logging in
       to the monitor will make AWS credentials available to the submitter, automatically.
    1. Set up an AWS credentials profile [as you would for the AWS CLI][aws-cli-credentials], and select that profile for the submitter
       to use.
    1. Or default to your AWS EC2 instance profile credentials if you are running a workstation in the cloud.

### Usage

After installation a "Deadline Cloud" menu is available the menu bar. Run "Submit to Deadline Cloud" to open the submitter.

### Application Interface Adaptor Development Workflow

#### Running the Adaptor on a Farm

If you have made modifications to the adaptor and wish to test your modifications on a live Deadline Cloud Farm
with real jobs, then we recommend using a [Service Managed Fleet](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html)
for your testing. We recommend performing this style of test if you have made any modifications that might interact with Deadline Cloud's
job attachments feature, or that could interact with path mapping in any way. We have implemented a developer feature in the 3ds Max submitter
plug-in that submits the Python wheel files for your modified adaptor along with your job submission and uses the modified adaptor to
run the submitted job.

You'll need to perform the following steps to substitute your build of the adaptor for the one in the service.

1. Using the submitter development workflow (See [Submitter Development Workflow](#submitter-development-workflow)), make sure that you are
   running 3ds Max with `DEADLINE_ENABLE_DEVELOPER_OPTIONS=true` enabled.
   
   **Windows (PowerShell):**
   ```powershell
   $env:DEADLINE_ENABLE_DEVELOPER_OPTIONS = "true"
   & $env:3DSMAX_EXECUTABLE
   ```
   
   **Windows (CMD):**
   ```cmd
   set DEADLINE_ENABLE_DEVELOPER_OPTIONS=true
   "%3DSMAX_EXECUTABLE%"
   ```

2. Clone the [deadline-cloud](https://github.com/aws-deadline/deadline-cloud) and
   [openjd-adaptor-runtime-for-python](https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python) repositories beside
   this one, and ensure that you `git checkout release` in each to checkout the latest `release` branch.

3. Build wheels for `openjd_adaptor_runtime`, `deadline` and `deadline_cloud_for_3ds_max`, place them in the `wheels/` folder in `deadline-cloud-for-3ds-max`.
   
   **Windows (PowerShell):**
   ```powershell
   # If you don't have the build package installed already
   pip install build
   
   # Use the provided script to build all wheels
   .\scripts\build_wheels.ps1
   
   # Or to clean and rebuild:
   .\scripts\build_wheels.ps1 -Clean
   ```
   
   **Linux/Mac:**
   ```bash
   # If you don't have the build package installed already
   $ pip install build
   ...
   $ ./scripts/build_wheels.sh
   ```

   Wheels should have been generated in the `wheels/` folder:

   ```bash
   $ ls ./wheels
   deadline_cloud_for_3ds_max-<version>-py3-none-any.whl
   deadline-<version>-py3-none-any.whl
   openjd_adaptor_runtime-<version>-py3-none-any.whl
   ```

4. Open the 3ds Max integrated submitter, and in the Scene Settings tab, enable the option 'Override Adaptor Wheels'. This option is only visible when the environment variable `DEADLINE_ENABLE_DEVELOPER_OPTIONS` is set to `true`.

5. Go to the Job Attachments tab and manually add the `wheels` directory as an input directory.

6. Submit your test job. The worker will create a Python virtual environment, install your development wheels, and use your modified adaptor to run the job.

#### Adaptor Schema Files

The adaptor uses two JSON schema files to define the contract between the 3ds Max submitter (running on artist workstations)
and the 3ds Max adaptor (running on cloud render workers):

- `src/deadline/max_adaptor/MaxAdaptor/schemas/init_data.schema.json` - Defines the initialization data passed once when the adaptor starts
- `src/deadline/max_adaptor/MaxAdaptor/schemas/run_data.schema.json` - Defines the per-task data passed for each frame/task to render

**Important:** Whenever you modify either of these schema files, you **must** also update the `integration_data_interface_version`
in `src/deadline/max_adaptor/MaxAdaptor/adaptor.py` following semantic versioning.

### Integration Test Workflow
Integration tests are located under `test/integ` directory of this repository. If you are adding
or modifying functionality, then you will want to be writing one or more integ tests to demonstrate that your
logic behaves as expected and that future changes do not accidentally break your change.

To run the integ tests, you need to:
1. Add 3dsMax and 3dsMax python executable to the PATH:
   
   For example, default path of 3dsMax python on Windows is:

```
C:\Program Files\Autodesk\3ds Max 2026\Python
```

In Powershell, you can set:

```powershell
$env:PATH = "C:\Program Files\Autodesk\3ds Max 2026;C:\Program Files\Autodesk\3ds Max 2026\Python;" + $env:PATH
```
2. Run command to install pip to this python executable:

```powershell
python -m ensurepip
```

3. Set the `3DSMAX_EXECUTABLE` environment variable to use `3dsmaxbatch`:

```powershell
$env:3DSMAX_EXECUTABLE = "3dsmaxbatch"
```

#### To run tests with 3ds Max's Python

4. Install all integration tests dependency to 3ds Max's Python:

```powershell
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install -r requirements-integ-testing.txt
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pip install "numpy<2"
```

5. Run submitter tests:

```powershell
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pytest test/integ -m submitter -o addopts="" -v
```

6. Run adaptor tests:

```powershell
& "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" -m pytest test/integ -m adaptor -o addopts="" -v
```

#### To run tests with hatch

This method is not recommended. Hatch uses Python 3.12 for testing, which causes conflicts with 3dsmax. To use hatch's integ test environment, downgrade the environment to 3.x to match 3ds Max. For example for 3ds Max 2026, downgrade hatch's integration environment to 3.11.

4. Use hatch to run all integ tests:

```bash
hatch run integ:test
```

5. (Optional) Use hatch to run submitter tests:

```bash
hatch run integ:test_submitters
```

6. (Optional) Use hatch to run adaptor tests:

```bash
hatch run integ:test_adaptors
```

### Common Problems encountered while running integration tests

1. PyWin32 issues when running integration tests. Pywin32 is used to bind Python to native Win32 API. To resolve this issue, please register the PyWin32 DLLs as suggested [here](https://github.com/mhammond/pywin32?tab=readme-ov-file#installing-via-pip) This must be done in an elevated shell with CAUTION:

```powershell
python -m pywin32_postinstall -install
```