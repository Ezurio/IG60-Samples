# Contact Tracing with the Sentrius IG60 Gateway and BT710 Sensor

This repo contains an example application for the Sentrius IG60 Greengrass. This example will scan, find, and connect to BT710 sensors. Then download contact tracing data, parse and send to AWS Iot Core.

[Sentrius IG60 Gateway](https://www.lairdconnect.com/iot-devices/iot-gateways/sentrius-ig60-serial-and-ig60-serial-lte-wireless-iot-gateways) |
[BT710 Sensor](https://www.lairdconnect.com/iot-devices/iot-sensors/sentrius-bt7x0-tracker-multi-sensor)

![BT710](https://connectivity-staging.s3.us-east-2.amazonaws.com/styles/product_thumbnail/s3/2020-06/BT710-Bluetooth-Covid-Tracker-Hero.png?itok=B_CPNI4N)

![IG60](https://connectivity-staging.s3.us-east-2.amazonaws.com/styles/product_thumbnail/s3/2020-01/ig60-transparent.png?itok=QTTqtco4)

```
                       XXXXX
                     XXX   XXX
           XXXXX   XX        XX
        XXX    XX XX          X XXXXXXX
        X        XX            X       XX
       X                                X
        X         AWS Cloud              X
        XX                              X
         XXXXXXX                       XX
               XX          XXXX    XXXX
                XXX      XXX   XXXX
                  XXXXXXX
                      ^
                      +
                (MQTT with TLS)
                      +
                      v
            +---------+----------+
            |                    |
            |  Sentrius IG60  |
            |                    |
            +---------+----------+
                      ^
                      +
                     BLE
                      +
                      v
           +----------+------------+
           |                       |
           |        BT710          |
           |                       |
           +-----------------------+

```

## Required Hardware

- **Sentrius IG60 Greengrass with internal BL654**
- **Sentrius IG60 Laird Linux with internal BL654** - it is also possible, but Greengrass must be installed
- **Sentrus IG60 Serial** - this is possible, but you must have a BL654 (451-0003) USB inserted
- **BT710** Sensor or **BT510CT** sensor

## Provision Sentrius IG60 Gateway - **this step must be completed before applcation can be deployed**

Before the application can be deployed, the gateway must first receive AWS Certificates, this is done in the provisioning process for the gateway. Please see documentation.

[Create IG60 Provisioning Server ](https://documentation.lairdconnect.com/Builds/IG60-SERIAL-GREENGRASS/latest/Content/Topics/5%20-%20Using%20the%20Device/Greengrass%20Getting%20Started/Create%20a%20Provisioning%20Server.htm)

## Prepare-package

This application will run as an AWS Greengrass Lambda. Therefore it must be packaged into a Lambda function [AWS Greengrass Docs](https://docs.aws.amazon.com/greengrass/latest/developerguide/what-is-gg.html)

**First, there is one modification required. Save src/ct_app_template.json as ct_app.json**
If you are using the USB BL654, change BL654_PORT to /dev/ttyUSB2

To aid in this task, there is a deployment bash script. This script will create a deploy folder, copy the source, download the dependencies, remove unnecessary files and zip up.

```
./deploy.sh
```

Required dependencies are listed in requirements.txt. Pip, zip, are required to package.

## Create a Lambda Function

This can be done manually from the AWS Console.

- Select Python3.7 as runtime
- upload .zip file from [Prepare deployment package](#Prepare-deployment-package)
- In Basic Settings, change the handler to app.handler
- Publish a version

## Deploy Lambda Function

For detailed steps, see Laird documentation [Deploy step](https://documentation.lairdconnect.com/Builds/IG60-SERIAL-GREENGRASS/latest/Content/Topics/5%20-%20Using%20the%20Device/Greengrass%20Getting%20Started/Configure%20Greengrass%20Deployment.htm)

In IoT Core, find your Greengrass Group

- Add the existing Lambda Function
- Edit the Lambda configuration
  - use ggc_user/ggc_group and Greengrass Container
  - Make the Lambda Long lived and keep running indefinitely
  - If you are using an LTE modem, set an environment variable "DBUS_SYSTEM_BUS_ADDRESS" with the value "unix:abstract=\_\_dbus\_proxy\_socket\_\_" to enable access to the Ofono D-Bus APIs

Add a local resource - Explicitly enable access to the BL654

- Device (not volume)
- Name is arbitrary. "ttyS2" works
- path is /dev/ttyS2
  - If you are using the BL654 dongle, use /dev/ttyUSB2
- Automatically add OS group permissions
- read and write access
- ensure that the resource is afilliated with the lambda

Add a subscription

- From the lambda to IoT Cloud
- topic is "laird/ig60/#" or "mg100-ct/#" for "mg100" format

Settings

- **Disable stream Manager**
- Enable cloud-watch logs
- Provide permissions to write to CloudWatch logs
