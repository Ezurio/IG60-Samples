#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import os
import json
import logging
import base64
from contact_tracing.log_file import DataLog

MQTT_BASE = "example/"

NODE_ID = os.getenv('AWS_IOT_THING_NAME') or 'NO_THING_NAME'


def prRed(skk):
    print("\033[91m {}\033[00m".format(skk))


def prMag(skk):
    print("\033[95m {}\033[00m".format(skk))


def prYellow(skk):
    print("\033[93m {}\033[00m".format(skk))


class Telem():
    def __init__(self):
        self.telem_topic = os.getenv(
            'MQTT_TELEM_TOPIC') or "laird/ig60/{}/ct/data".format(NODE_ID)

        self.status_topic = os.getenv(
            'MQTT_STATUS_TOPIC') or "laird/ig60/{}/ct/status".format(NODE_ID)

    def register_status_topic(self, topic):
        self.status_topic = topic

    def register_telem_topic(self, topic):
        self.telem_topic = topic


class IoTCoreMqttClient(Telem):
    def __init__(self):
        super().__init__()
        import greengrasssdk
        self.client = greengrasssdk.client('iot-data')
        self.logger = logging.getLogger(__name__)

    def status(self, payload):
        resp = {"status": payload}
        self.client.publish(topic=self.status_topic, payload=json.dumps(resp))
        self.logger.info("status topic: {}, payload: {}".format(
            self.status_topic, resp))

    def publish_b64(self, payload, dev_id):
        topic = self.telem_topic + f"/b64/{dev_id}"
        s_payload = str(base64.b64encode(payload), "ascii")
        resp = {"payload": s_payload}
        self.client.publish(topic=topic, payload=json.dumps(resp))

    def publish_json(self, payload, dev_id):
        topic = self.telem_topic + f"/json/{dev_id}"
        resp = DataLog(payload).serialize()
        self.client.publish(topic=topic, payload=resp)


class LocalPrint(Telem):
    def __init__(self):
        super().__init__()

    def status(self, payload):
        resp = {"status": payload}
        prMag("status topic: {}, payload: {}".format(self.status_topic, resp))

    def publish_b64(self, payload, dev_id):
        topic = self.telem_topic + f"/b64/{dev_id}"
        try:
            s_payload = str(base64.b64encode(payload), "ascii")
            resp = {"ble_scan": s_payload}
            prYellow("tag topic: {}, payload: {}".format(topic, resp))
        except Exception as e:
            print(e)

    def publish_json(self, payload, dev_id):
        topic = self.telem_topic + f"/json/{dev_id}"
        resp = DataLog(payload).serialize()
        prYellow("tag topic: {}, payload: {}".format(topic, resp))
