#
# copyright (c) 2024 Ezurio LLC.
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import logging
from typing import List
import sb.adv as bt_adv
from .adv_time import adv_time, local_time
logger = logging.getLogger(__name__)

global_target_list = []
RSSI_THRESHOLD = -80


def establish_targets(targetl: List[str]):
    global global_target_list
    global_target_list = targetl


def add_target(target: bt_adv.ScanRes) -> bool:
    #checks basic criteria for added a device to connection list. Check RSSI is strong enough. Check that target is on the list
    global global_target_list

    if target.rssi < RSSI_THRESHOLD:
        return False
    if global_target_list == []:
        return target.data_available
    else:
        return target.mac in global_target_list and target.data_available


async def decision(*targets: bt_adv.ScanRes, max_con: int = 1):
    #takes in scan results, and makes a decision on which targets to connect to
    global global_target_list
    targetl = []
    for target in targets:
        try:
            logger.debug(
                f"{target.mac} rssi:{target.rssi} time:{local_time(target.epoch)} has_data:{target.data_available} has_epoch:{target.has_epoch}"
            )
            if add_target(target):
                if target.mac not in targetl:
                    targetl.append(target.mac)
                if len(targetl) >= max_con:
                    break
        except Exception as e:
            logger.error(f'decision exception ->  {e} - {repr(target)}  ')
    return targetl
