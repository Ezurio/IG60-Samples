/*
 * Demonstrates how to use the journalctl module to
 * retrieve sytem log entries and publish them via
 * MQTT.
 */


const Journalctl = require("journalctl");
const ggSdk = require('aws-greengrass-core-sdk');

const journalctl = new Journalctl();

const topic = 'journalctl/' + process.env.AWS_IOT_THING_NAME;
console.log('Logging journal to: ' + topic);

const iotClient = new ggSdk.IotData();

journalctl.on('event', (event) => {
    // Log to CloudWatch
    console.log(event);
    // Send via MQTT (ignore errors)
    iotClient.publish({
        topic: 'journalctl/' + process.env.NODE_ID,
        payload: JSON.stringify(event),
        queueFullPolicy: 'AllOrError'
        }, (err, data) => {});
});

//
// Shutdown when terminated
//
process.on('SIGINT', function() {
    console.log("Caught interrupt signal");
    journalctl.stop();
});

// This is a handler (not used)
exports.handler = function handler(event, context) {
    console.log(event);
    console.log(context);
};
