#
# copyright (c) 2024 Ezurio LLC.
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import os
import json
import logging

def prRed(skk):
    print("\033[91m {}\033[00m".format(skk))

def prMag(skk):
    print("\033[95m {}\033[00m".format(skk))

def prYellow(skk):
    print("\033[93m {}\033[00m".format(skk))

class IoTCoreMqttClient():
    def __init__(self, id = None):
        import greengrasssdk
        self.client = greengrasssdk.client('iot-data')
        self.logger = logging.getLogger(__name__)
        self.id = id or 'UNKNOWN'
        self.topic = "laird/ig60/{}/bt510".format(self.id)

    def publish(self, payload, dev_id):
        topic = self.topic + f"/json/{dev_id}"
        self.client.publish(topic=topic, payload=json.dumps(payload))

class LocalPrint():
    def __init__(self, id = None):
        self.id = id or '000000000000000'
        self.topic = "laird/ig60/{}/bt510".format(self.id)

    def publish(self, payload, dev_id):
        topic = self.topic + f"/json/{dev_id}"
        prYellow("tag topic: {}, payload: {}".format(topic, json.dumps(payload)))
