#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import asyncio
import aioserial
import sb.command as bt_cmd
import sb.response as bt_resp
import logging
from .smp import SmpFileResp
import os
import time
import binascii

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

LOG_CT = "/log/ct"
PARAMS = "/lfs/params.txt"


class Bt510Ct():
    last_conn_mac = ""
    bin_format = False

    @classmethod
    def set_payload_format(cls, val: str):
        cls.payload_format = val

    @classmethod
    def set_client(cls, client):
        cls.client = client

    def __init__(self,
                 mac: str,
                 inst: aioserial.aioserial,
                 lock: asyncio.Lock,
                 binary=False):
        self.mac = mac
        self.aio_serial_inst = inst
        self.queue = asyncio.Queue()
        self.conn_handle = 0
        self.started = 0
        self.conn_lock = lock
        self.binary = bin

    def get_queue(self):
        return self.queue

    async def work(self):
        try:
            res = await asyncio.wait_for(self._connect(), timeout=2.5)
            if res:
                await asyncio.wait_for(self._get_file(LOG_CT), timeout=45)
                await asyncio.wait_for(self._disconnect(), timeout=1)
                await asyncio.wait_for(self._publish(), timeout=2)
        except asyncio.TimeoutError:
            logger.info(f'connection timeout {self.mac}')

    async def _publish(self):
        if self.file_data:
            logger.debug("publish")
            if Bt510Ct.payload_format == "json":
                Bt510Ct.client.publish_json(self.file_data, self.mac)
            elif Bt510Ct.payload_format == "json_legacy":
                Bt510Ct.client.publish_json_legacy(self.file_data, self.mac)
            elif Bt510Ct.payload_format == "mg100":
                Bt510Ct.client.publish_mg100(self.file_data, self.mac)
            else:
                Bt510Ct.client.publish_b64(self.file_data, self.mac)

    async def _connect(self):
        handle: str = None
        try_count: int = 0
        async with self.conn_lock:
            Bt510Ct.last_conn_mac = self.mac
            connect = bt_cmd.get_conn_cmd(self.mac)
            while not handle and try_count < MAX_RETRIES:
                await self.aio_serial_inst.write_async(connect)
                resp = await self.queue.get()
                handle = bt_resp.get_handle_from_conn_resp(resp)
                if handle:
                    logger.debug(f"handle {self.mac} -> {repr(resp)}")
                else:
                    logger.debug(f"handle error -> {repr(resp)}")
                self.queue.task_done()
                try_count += 1
            Bt510Ct.last_conn_mac = ""
        if handle:
            self.conn_handle = int(handle, 16)
            return handle

    async def _disconnect(self):
        async with self.conn_lock:
            logger.debug(f"{self.mac} disconnect")
            await self.aio_serial_inst.write_async(
                bt_cmd.get_disconnect_cmd(self.conn_handle))

    async def _get_file(self, filename: str):
        file = SmpFileResp(self.mac, filename)
        temp = file.get_file_cmd(self.conn_handle)
        logger.debug(f"{self.mac} write {temp}")
        await self.aio_serial_inst.write_async(temp)

        while True:
            resp = await self.queue.get()
            ##todo remove sb specific portion
            if "evt_hvx:" in resp:
                (_, _, data) = bt_resp.sb_notif_decode(resp)
                #if file.data returns true, response. Else, wait for more data
                if file.data(data):
                    if file.is_complete():
                        self.file_data = file.read()
                        logger.debug('file data: {}'.format(self.file_data.hex()))
                        break
                    else:
                        temp = file.get_cmd(self.conn_handle)
                        async with self.conn_lock:
                            logger.debug(f"{self.mac} write ${temp}")
                            await self.aio_serial_inst.write_async(temp)
            else:
                logger.error(repr(resp))
                break

            self.queue.task_done()
