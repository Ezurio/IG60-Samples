#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import logging
import asyncio
import json
import os
from contact_tracing.tasks import task_main
from contact_tracing.decision import establish_targets
from contact_tracing.btx10ct import Bt510Ct

from bt_manager import startup

if os.uname()[4] == 'x86_64':
    from publish import LocalPrint as Client
else:
    from publish import IoTCoreMqttClient as Client
client = Client()

config_file = "ct_app.json"
with open(config_file, 'r') as fp:
    config = json.load(fp)

if os.uname()[4] == 'x86_64':
    port = config["bl654_port"]
    logging.basicConfig(
        format='%(asctime)s  %(levelname)s  %(filename)s - %(message)s',
        level="DEBUG")
else:
    port = "/dev/ttyS2"
    logging.basicConfig(
        format='%(asctime)s  %(levelname)s  %(filename)s - %(message)s')

logger = logging.getLogger(__name__)
logger.info(config)


def apply_config(config):
    ''' apply applcication configuration settings '''
    logger.info(config)
    startup(port, config["sb_app"], config["sb_app_folder"], config["sb_at"])
    establish_targets(config["decision"]["targets"])

    Bt510Ct.set_bin_format(config["binary_format"])
    Bt510Ct.set_client(client)
    client.status(f"startup - {config['sb_app']} ")


apply_config(config)
asyncio.run(task_main(port, config["baudrate_str"]))


def handler():
    return
