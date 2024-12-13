#
# copyright (c) 2024 Ezurio LLC.
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.

import logging
import asyncio
import aioserial
from typing import List

import sb.command as bt_cmd
import sb.response as bt_resp
import sb.adv as bt_adv
from .adv_time import adv_time
from .decision import decision
from .btx10ct import Bt510Ct

logger = logging.getLogger(__name__)


async def arbiter(aioserial_instance: aioserial.AioSerial, targets):
    """ receive all serial responses - send to specific device NOTE: This implementation is SmartBasic specific """

    handle_to_mac = {}
    while True:
        resp = (await
                aioserial_instance.read_until_async()).decode(errors='ignore')

        try:
            bt_ident = bt_resp.handle_resp(resp, Bt510Ct.last_conn_mac)
            if bt_ident.mac:
                #here is the SB specific portion
                if resp.startswith("connA"):
                    handle_to_mac[bt_ident.handle] = bt_ident.mac
                else:
                    q = targets[bt_ident.mac].get_queue()
                    await q.put(resp)
            else:
                this_mac = handle_to_mac[bt_ident.handle]
                q = targets[this_mac].get_queue()
                await q.put(resp)

        except Exception as e:
            if resp.startswith("##"):
                logger.warning(repr(resp))
            else:
                logger.error(f'receive exception ->  {e} - {repr(resp)}  ')


async def create_tasks(*target_list: bt_adv.ScanRes,
                       inst: aioserial.AioSerial):
    if len(target_list) == 0:
        return
    logger.debug("starting connections ")
    conn_lock = asyncio.Lock()
    targets = {}
    tasks = []
    for target in target_list:
        logger.debug(f"connecting to {target} ")
        t = Bt510Ct(target, inst, conn_lock)
        targets[target] = t
        task = asyncio.create_task(t.work())
        tasks.append(task)

    rec_task = asyncio.create_task(arbiter(inst, targets))
    ret = await asyncio.gather(*tasks, return_exceptions=True)
    if ret:
        logger.info(ret)
    rec_task.cancel()


async def scan_and_filter(inst: aioserial.AioSerial):
    target_list = []
    while True:
        #before scaning, start advertising time
        adv = bt_cmd.advertise(adv_time())
        await inst.write_async(adv)
        try:
            target_list = await asyncio.wait_for(scan(inst), timeout=2.2)
        except asyncio.TimeoutError:
            logger.warning("scan timeout")
            pass

        if target_list:
            logger.info(f"scan resposne length {len(target_list)} ")
            target_list = await decision(*target_list)
        if target_list:
            logger.info(f"target list - {target_list} ")
            await create_tasks(*target_list, inst=inst)


async def scan(inst: aioserial.AioSerial) -> List[bt_adv.ScanRes]:
    await inst.write_async(bt_cmd.get_scan_cmd())
    ret: List[bt_adv.ScanRes] = []
    while True:
        resp = (await inst.read_until_async())
        try:
            adv = bt_adv.handler(resp)
            ret.append(adv)
        except AttributeError as e:
            logger.warning(f"scan response attribute warning {e}")
        except bt_adv.ScanTimeout:
            break
    return ret


async def task_main(port, baudrate) -> None:
    inst = aioserial.AioSerial(port=port, baudrate=baudrate, rtscts=True)
    asyncio.create_task(scan_and_filter(inst))
    while True:
        ## this will allow developers to have a responsive ctr-C
        await asyncio.sleep(1)
