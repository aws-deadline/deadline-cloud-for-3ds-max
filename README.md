# AWS Deadline Cloud for 3ds Max


[![pypi](https://img.shields.io/pypi/v/deadline-cloud-for-3ds-max.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-3ds-max)
[![python](https://img.shields.io/pypi/pyversions/deadline-cloud-for-3ds-max.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-3ds-max)
[![license](https://img.shields.io/pypi/l/deadline-cloud-for-3ds-max.svg?style=flat)](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/mainline/LICENSE)

### Disclaimer
---
This GitHub repository is an example integration with AWS Deadline Cloud that is intended to only be used for testing and is subject to change. This code is an alpha release. It is not a commercial release and may contain bugs, errors, defects, or harmful components. Accordingly, the code in this repository is provided as-is. Use within a production environment is at your own risk!

Our focus is to explore a variety of software applications to ensure we have good coverage across common workflows. We prioritized making this example available earlier to users rather than being feature complete.

This example has been used by at least one internal or external development team to create a series of jobs that successfully rendered. However, your mileage may vary. If you have questions or issues with this example, please start a discussion or cut an issue.
---

AWS Deadline Cloud for 3ds Max is a python package that allows users to create [AWS Deadline Cloud][deadline-cloud] jobs from within 3ds Max. Using the [Open Job Description (OpenJD) Adaptor Runtime][openjd-adaptor-runtime] this package also provides a command line application that adapts 3ds Max's command line interface to support the [OpenJD specification][openjd].

[deadline-cloud]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/what-is-deadline-cloud.html
[deadline-cloud-client]: https://github.com/aws-deadline/deadline-cloud
[openjd]: https://github.com/OpenJobDescription/openjd-specifications/wiki
[openjd-adaptor-runtime]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
[openjd-adaptor-runtime-lifecycle]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python/blob/release/README.md#adaptor-lifecycle

## Compatibility

This library requires:

1. 3ds Max 2024,
1. Python 3.9 or higher; and
1. Windows operating system.

## Submitter

This package provides a 3ds Max plugin that creates jobs for AWS Deadline Cloud using the [AWS Deadline Cloud client library][deadline-cloud-client]. Based on the loaded scene it determines the files required, allows the user to specify render options, and builds an [OpenJD template][openjd] that defines the workflow.

## Adaptor

The 3ds Max Adaptor implements the [OpenJD][openjd-adaptor-runtime] interface that allows render workloads to launch 3ds Max and feed it commands. This gives the following benefits:
* a standardized render application interface,
* sticky rendering, where the application stays open between tasks,

Jobs created by the submitter use this adaptor by default.

### Getting Started

The adaptor can be installed by the standard python packaging mechanisms:
```sh
$ pip install deadline-cloud-for-3ds-max
```

After installation it can then be used as a command line tool:
```sh
$ 3dsmax-openjd --help
```

For more information on the commands the OpenJD adaptor runtime provides, see [here][openjd-adaptor-runtime-lifecycle].

## Versioning

This package's version follows [Semantic Versioning 2.0](https://semver.org/), but is still considered to be in its 
initial development, thus backwards incompatible versions are denoted by minor version bumps. To help illustrate how
versions will increment during this initial development stage, they are described below:

1. The MAJOR version is currently 0, indicating initial development. 
2. The MINOR version is currently incremented when backwards incompatible changes are introduced to the public API. 
3. The PATCH version is currently incremented when bug fixes or backwards compatible changes are introduced to the public API. 

## Security

See [CONTRIBUTING](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/release/CONTRIBUTING.md#security-issue-notifications) for more information.

## Telemetry

See [telemetry](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/blob/release/docs/telemetry.md) for more information.

## License

This project is licensed under the Apache-2.0 License.
