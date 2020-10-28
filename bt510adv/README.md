# Data Collection from BT510 sensors using the Sentrius IG60 Gateway

This repo contains an example application for the Sentrius IG60 Greengrass, that will scan for and decode advertisement packets from BT510 sensors and forward them to AWS IoT.

[Sentrius IG60 Gateway](https://www.lairdconnect.com/iot-devices/iot-gateways/sentrius-ig60-serial-and-ig60-serial-lte-wireless-iot-gateways) |
[BT510 Sensor](https://www.lairdconnect.com/iot-devices/iot-sensors/bt510-bluetooth-5-long-range-ip67-multi-sensor)

## Required Hardware

- **Sentrius IG60 Greengrass with internal BL654**
- **BT510** Sensor

## Provision Sentrius IG60 Gateway - **this step must be completed before application can be deployed**

Before the application can be deployed, the gateway must first receive AWS Certificates, this is done in the provisioning process for the gateway. Please see documentation.

[Create IG60 Provisioning Server ](https://documentation.lairdconnect.com/Builds/IG60-SERIAL-GREENGRASS/latest/Content/Topics/5%20-%20Using%20the%20Device/Greengrass%20Getting%20Started/Create%20a%20Provisioning%20Server.htm)

## Prepare and package the Lambda function

This application will run as an AWS Greengrass Lambda. Therefore it must be packaged into a Lambda function [AWS Greengrass Docs](https://docs.aws.amazon.com/greengrass/latest/developerguide/what-is-gg.html)

To aid in this task, there is a deployment bash script and Windows batch file. This script will create a deploy folder, copy the source, download the dependencies, and create a ZIP file.

```
$ ./deploy.sh
```
or
```
C:\>deploy.bat
```

Required dependencies are listed in requirements.txt. Pip, zip, are required to package.

## Create a Lambda Function

This can be done manually from the AWS Console.

- Select Python3.7 as runtime
- Upload the lambda_deploy.zip file from [Prepare deployment package](#Prepare-deployment-package)
- In Basic Settings, change the handler to app.handler
- Publish a version

## Deploy the Lambda Function

For detailed steps, see Laird documentation [Deploy step](https://documentation.lairdconnect.com/Builds/IG60-SERIAL-GREENGRASS/latest/Content/Topics/5%20-%20Using%20the%20Device/Greengrass%20Getting%20Started/Configure%20Greengrass%20Deployment.htm)

In IoT Core, find your Greengrass Group

- Add the existing Lambda Function
- Edit the Lambda configuration
  - use ggc_user/ggc_group and Greengrass Container
  - Make the Lambda Long lived and keep running indefinitely

Add a local resource to enable access to the BL654 device from the containerized Lambda

- Device (not volume)
- Name is arbitrary. "ttyS2" works
- path is /dev/ttyS2
- Automatically add OS group permissions
- Read and write access
- Ensure that the resource is afilliated with the Lambda

Add a subscription

- From the lambda to IoT Cloud
- Set the topic as "laird/ig60/+/bt510/#"

The Lambda will publiish to this topic using the IG60 "Thing Name" and BT510 MAC address, for example:
```
laird/ig60/MyIG60ThingName/bt510/json/01E8B7601E37D1
```

Settings

- **Disable stream Manager**
- Enable cloud-watch logs
- Provide permissions to write to CloudWatch logs

## Notes
This Lambda deploys a pre-built version of the smartBASIC AT Command application for BLE.  You can find the source in the [BL654 Applications repository](https://github.com/LairdCP/BL654-Applications).  There is also [documentation on the BL654 product page](https://www.lairdconnect.com/documentation/user-guide-bl65x-interface-application).
