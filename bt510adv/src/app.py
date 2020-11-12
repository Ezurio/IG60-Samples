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
import platform
import bt_manager
import bt_scan

CONFIG_PORT = os.getenv('BL654_PORT') or '/dev/ttyS2'
CONFIG_BAUD = int(os.getenv('BL654_BAUD') or '115200')
NODE_ID = os.getenv('AWS_IOT_THING_NAME') or 'NO_THING_NAME'

SB_APP = "atcmd"
SB_APP_FOLDER = './'

SB_AT_STARTUP = [
    "at+cfg 213 1",
    "at+cfg 216 27",
    "at+cfg 211 247",
    "at+cfg 212 247",
    "atz"
]

# This is the incoming message handler (not used)
def handler():
    return

# Set up logging
if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s  %(levelname)s  %(filename)s - %(message)s',
        level=logging.DEBUG)
else:
    logging.basicConfig(
        format='%(asctime)s  %(levelname)s  %(filename)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)

# Only print messages if run from command line
if __name__ == "__main__":
    from publish import LocalPrint as Client
else:
    from publish import IoTCoreMqttClient as Client

client = Client(NODE_ID)

# Start BT manager: configure AT commands and download compiled SB app
bt_manager.startup(CONFIG_PORT, SB_APP, SB_APP_FOLDER, SB_AT_STARTUP)

asyncio.run(bt_scan.task_main(CONFIG_PORT, CONFIG_BAUD, client))
