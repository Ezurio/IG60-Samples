#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.

from collections import namedtuple
import binascii
from construct import Struct,  Byte,  BitStruct, BitsInteger,\
    Flag, Array, Int16ul, Int32ul,  Switch
import logging
logger = logging.getLogger(__name__)

AD_TYPE = 17

TRACK_RECORD = Struct("profile" / Byte, "epoch" / Int32ul, "tx_power" / Byte,
                      "Motion" / Byte, "Reserved" / Array(4, Byte))

CT_ADV = Struct(
    "company_id" / Int16ul, "protocol_id" / Int16ul, "network_id" / Int16ul,
    "flags" / BitStruct(
        "reserved" / BitsInteger(4),
        "LOW_BATTERY" / Flag,
        "HAS_MOTION" / Flag,
        "HAS_LOG_DATA" / Flag,
        "HAS_EPOCH_TIME" / Flag,
        "reserved" / BitsInteger(8),
    ), "DeviceID" / Array(6, Byte), "record_type" / Byte,
    "record_data" / Switch(lambda ctx: ctx.record_type, {
        0: TRACK_RECORD,
        AD_TYPE: TRACK_RECORD,
    },
                           default=Array(11, Byte)))


def parse(data: bytes):
    """ parse the more interesting parts """
    ct_adv = binascii.unhexlify(data)
    return CT_ADV.parse(ct_adv)


# offset where ADV data begins in bytes
ADV_DATA_OFFSET = 18
# offset where mfg specific ADV data begins in bytes
MFG_DATA_OFFSET = 29
#size of record that we are looking at is 26 * 2
RECORD_DATA_SIZE = 52

ADV_LENGTH_PASSIVE = 88
ADV_LENGTH_ACTIVE = 118

ScanRes = namedtuple('Adv', [
    'mac', 'data', 'rssi', 'epoch', 'data_available', 'has_epoch', 'motion',
    'low_batt'
])


class ScanTimeout(Exception):
    def __init__(self):
        pass


def handler(adv: bytes) -> ScanRes:
    """ convert the SmartBasic advertisement response to object, with mac, data and rssi """
    if len(adv) != ADV_LENGTH_PASSIVE:
        if adv == b"scan:timeout\n":
            raise ScanTimeout()
        raise AttributeError(f"adv unexpected format length {len(adv)} {adv}")
    try:
        adv_s = str(adv, "ascii")
    except UnicodeDecodeError:
        print(f"unicode decode error {adv}")
        raise AttributeError(f"adv unexpected format")
    target = adv[MFG_DATA_OFFSET:MFG_DATA_OFFSET + RECORD_DATA_SIZE]
    parsed_data = parse(target)
    advl = adv_s.rstrip("\n").split(" ")
    if len(advl) != 4:
        raise AttributeError("not able to handle adv format")
    mac = advl[0].lstrip("adv:")
    data = advl[1]
    rssi = int(advl[3])
    epoch = 0
    if parsed_data.record_type in [AD_TYPE, 0]:
        epoch = parsed_data.record_data.epoch

    return ScanRes(mac, data, rssi, epoch, parsed_data.flags.HAS_LOG_DATA,
                   parsed_data.flags.HAS_EPOCH_TIME,
                   parsed_data.flags.HAS_MOTION, parsed_data.flags.LOW_BATTERY)


if __name__ == "__main__":

    test = [
        b"adv:01CBEC4C68885D 0201061BFF770081FFFFFF01005D88684CECCB00004291365F000000000000 0 -63",
        b"adv:01FF26414D2F09 0201061BFF770081FFFFFF0300092F4D4126FF00004491365F000000000000 0 -58",
        b"adv:01D7CB5B96A448 0201061BFF770081FFFFFF010048A4965BCBD700004091365F000000000000 0 -61"
    ]
    for t in test:
        print(handler(t))