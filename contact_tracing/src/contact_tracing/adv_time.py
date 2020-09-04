#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import sb.command as bt_cmd
import logging
import time
import calendar
import struct
import binascii
logger = logging.getLogger(__name__)

COMPANY_ID = 0x0077
PROTOCOL_ID = 0xFF82
NETWORK_ID = 0xFFFF
FLAGS = 1
DEVICE_ID = 0
AD_RECORD_TYPE = 0

#AD tracking record
PROFILE = 0
TXPOWER = 0
MOTION = 0
HW_ID = 0x50


def local_time(t: int) -> str:
    return time.ctime(t)


def adv_time() -> bytes:
    time_cmd = (calendar.timegm(time.gmtime()))
    ad_record = struct.pack('<BLbBL', PROFILE, time_cmd, TXPOWER, MOTION,
                            HW_ID)
    adv = struct.pack('<HHHH', COMPANY_ID, PROTOCOL_ID, NETWORK_ID, FLAGS)
    return binascii.hexlify(adv) + b'00000000000000' + binascii.hexlify(
        ad_record)


if __name__ == "__main__":
    time_cmd = hex(calendar.timegm(time.gmtime())).lstrip("0x")
    print(time_cmd)
    timer = adv_time()
    print(f"{timer}   {len(timer)}")
