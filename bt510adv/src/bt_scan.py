#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.

import logging
import binascii
import struct
import asyncio
import aioserial
import time

logger = logging.getLogger(__name__)

APP_CMD = 'AT+RUN \"atcmd\"'

BT_SCAN_FORMAT = 'AT+SFMT 1'
BT_SCAN_CMD = 'AT+LSCN {},\"\\FF\\77\\00\\01\"'

SREG_SET_CMD = 'AT S{}={}'
SREG_STORE_CMD = 'AT&W'

RESET_CMD = 'ATZ\r'

SREGISTER_VALUES = [
    (211, 80),  # Scan interval
    (212, 80)   # Scan window
]

def parse_bt510_data(mac, rssi, data):
    # Refer to the BT510 User Guide for details on the advertisement format
    adv = { 'mac' : mac, 'rssi' : rssi }
    adv['network_id'] = struct.unpack('<H', data[9:11])[0]
    adv['flags'] = struct.unpack('<H', data[11:13])[0]
    adv['bd_addr'] = binascii.hexlify(data[18:12:-1]).decode('utf-8').upper()
    adv['record_type'] = int(data[19])
    adv['record_number'] = struct.unpack('<H', data[20:22])[0]
    adv['epoch'] = struct.unpack('<I', data[22:26])[0]
    adv['data'] = struct.unpack('<I', data[26:30])[0]
    adv['reset_count_lsb'] = int(data[30])
    return adv

def parse_adv(adv_str):
    """ Convert the advertisement response to object, with mac, data and rssi """
    try:
        advl = adv_str.rstrip().split(' ')
        mac = advl[1]
        rssi = int(advl[2])
        data = binascii.unhexlify(advl[3].strip('"'))
        # Data has already been filtered for BT510 so just parse it
        return parse_bt510_data(mac, rssi, data), mac
    except Exception as e:
        logger.error('Failed to parse advertisement: {} {}'.format(advl, e))

async def cmd(inst, req_str, timeout=3):
    inst.timeout = timeout
    await inst.write_async((req_str+'\r').encode())
    resp_bytes = await inst.read_until_async('\r'.encode())
    resp = resp_bytes.decode('utf-8')
    logger.debug('Command {} response: {}'.format(req_str, resp))
    return resp

async def scan(inst, client, scan_timeout):
    timeout = scan_timeout if scan_timeout is not None else 0
    logger.info('Starting LE scan for' + ('ever' if timeout == 0 else ' {} seconds'.format(timeout)))
    resp = await cmd(inst, BT_SCAN_FORMAT)
    # Don't await the 'OK' since scan results can return first
    resp = await cmd(inst, BT_SCAN_CMD.format(int(timeout)), 0)
    while True:
        inst.timeout = None
        resp_bytes = (await inst.read_until_async('\r'.encode()))
        if len(resp_bytes) == 0:
            return
        logger.debug('Raw adv: {}'.format(resp_bytes))
        try:
            resp = resp_bytes.decode('utf-8').lstrip()
            if resp.startswith('AD'):
                resp = str(resp_bytes, 'ascii')
                adv, mac = parse_adv(resp)
                if adv:
                    logger.info('Publishing advertisement: {}'.format(adv))
                    client.publish(adv, mac)
            elif resp.startswith('OK'):
                pass
            else:
                logger.warning('Unexpected response during scan: {}'.format(resp))
        except UnicodeDecodeError:
            logger.warning('adv unexpected format')
        except Exception as e:
            logger.warning(f'scan failed {e}')

async def scan_and_filter(inst, client, scan_timeout=None):
    while True:
        try:
            await asyncio.wait_for(scan(inst, client, scan_timeout), scan_timeout)
        except asyncio.TimeoutError:
            logger.info('Scan complete')

async def task_main(port, baudrate, client):
    inst = aioserial.AioSerial(port=port, baudrate=baudrate, rtscts=True)
    # Make sure app is running
    inst.send_break(.5)
    await cmd(inst, APP_CMD)
    # App doesn't respond until first input
    await cmd(inst, '')
    # Configure S-registers
    for srec in SREGISTER_VALUES:
        await cmd(inst, SREG_SET_CMD.format(srec[0], srec[1]))
    await cmd(inst, SREG_STORE_CMD)
    # Reset (no response)
    await inst.write_async(RESET_CMD.encode())
    # Wait for module to reboot
    time.sleep(2)
    # Start app again
    await cmd(inst, APP_CMD)
    await cmd(inst, '')
    # Start the scanning task
    asyncio.create_task(scan_and_filter(inst, client))
    while True:
        ## this will allow developers to have a responsive ctr-C
        await asyncio.sleep(1)