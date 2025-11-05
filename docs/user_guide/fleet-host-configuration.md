# Fleet Host Configuration

Before setting up the 3ds Max submitter, please configure the Deadline fleet as follows.

3ds Max is a popular Digital Content Creation tool provided by Autodesk. 3ds Max runs on Windows, and requires administrative access to install onto a host. Because of the administrative requirement, Deadline Cloud recommends installing 3ds Max on to the worker host using Host Configuration Scripts.

[Custom fleet host configuration scripts](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/smf-admin.html) allow you to perform administrative tasks, such as software installation, on your service-managed fleet workers. These scripts run with elevated privileges, giving you the flexibility to configure your workers for your system.

## Examples

We have examples for 3ds Max 2024, 2025 with V-Ray and examples integrating with plugins such as tyFlow. To request additional examples, please suggest ideas to our [discussion forum](https://github.com/aws-deadline/deadline-cloud-for-3ds-max/discussions).

For complete host configuration script examples, visit: [https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/host_configuration_scripts/3dsmax](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/host_configuration_scripts/3dsmax)

Note: While the examples install specific 3ds Max versions, Deadline Cloud's submitter supports 3ds Max 2025, 2026 as well. The installation script should work equivalently for 3ds Max 2025, 2026.
