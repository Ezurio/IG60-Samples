# Node.JS journalctl Example

This directory contains a sample application to forward the IG60 system journal via both MQTT and CloudWatch logs.

## How to deploy

- Copy the contents of this directory to another directory
- Change to the new directory
- Run the following command
    npm install aws-greengrass-core-sdk journalctl
- Zip the entire directory (including the "node_modules" subdirectory)
- Deploy this ZIP file as a Lambda, with the following settings:
    - Select "Make this function long lived and keep it running indefinitely"
    - Select "No container"
    - Set the user ID (UID) to 201, and the group ID (GID) to 1002
