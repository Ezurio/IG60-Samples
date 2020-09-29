#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import binascii
import crcmod.predefined
import json
import struct
import timeit
import time
import logging
logger = logging.getLogger(__name__)


def str_end_rev(input: str) -> str:
    """ ABCD -> CDAB ; reverse order, but groupd by two  """
    return "".join([b + a for a, b in zip(input[::2], input[1::2])])[::-1]


class LogCtHeaderP1():
    def __init__(self, data: bytes):
        if len(data) != 24:
            raise ValueError(" P1 Log header should be 24 bytes")
        self.entry_protocol_version = int.from_bytes(data[0:2],
                                                     byteorder="little",
                                                     signed=False)
        self.entry_size = int.from_bytes(data[2:4],
                                         byteorder="little",
                                         signed=False)
        self.entry_count = int.from_bytes(data[4:6],
                                          byteorder="little",
                                          signed=False)

        self.device_id = str_end_rev(str(data[6:12].hex()))

        self.device_time = int.from_bytes(data[12:16],
                                          byteorder="little",
                                          signed=False)

        self.log_size = int.from_bytes(data[16:20],
                                       byteorder="little",
                                       signed=False)

        self.last_upload = int.from_bytes(data[20:24],
                                          byteorder="little",
                                          signed=False)

    def __repr__(self) -> str:
        return f"""Log Header 1 ->
        protocol: {self.entry_protocol_version}  
        size: {self.entry_size}
        count: {self.entry_count}  
        deviceID: {self.device_id}
        device_time: {self.device_time} 
        log_size: {self.log_size} 
        last_upload: {self.last_upload}"""


class LogCtHeaderP2():
    def __init__(self, data: bytes):
        self.fw_version = str(data[0:4].hex())
        self.devices_seen = int.from_bytes(data[4:6],
                                           byteorder="little",
                                           signed=False)

        self.network_id = int.from_bytes(data[6:8],
                                         byteorder="little",
                                         signed=False)

        self.ad_interval_ms = int.from_bytes(data[8:10],
                                             byteorder="little",
                                             signed=False)

        self.log_interval_min = int.from_bytes(data[10:12],
                                               byteorder="little",
                                               signed=False)

        self.scan_interval_sec = int.from_bytes(data[12:14],
                                                byteorder="little",
                                                signed=False)

        self.battery_level = int.from_bytes(data[14:15],
                                            byteorder="little",
                                            signed=False)

        self.scan_dur_sec = int.from_bytes(data[15:16],
                                           byteorder="little",
                                           signed=False)
        self.profile = int.from_bytes(data[16:17],
                                      byteorder="little",
                                      signed=False)
        self.rssi_threshold = int.from_bytes(data[17:18],
                                             byteorder="little",
                                             signed=True)
        self.tx_power = int.from_bytes(data[18:19],
                                       byteorder="little",
                                       signed=True)

        self.up_time_sec = int.from_bytes(data[19:23],
                                          byteorder="little",
                                          signed=False)

        self.crc = str(data[23:25].hex())

    def __repr__(self) -> str:
        return f"""Log Header 2 -> 
        fw_version: {self.fw_version} 
        devices_seen: {self.devices_seen}  
        network_id: {self.network_id} 
        ad_interval_ms: {self.ad_interval_ms}
        log_interval_min: {self.log_interval_min}
        scan_interval_sec: {self.scan_interval_sec}
        battery_level_mv: {self.battery_level}
        scan_duration_sec: {self.scan_dur_sec}
        profile: {self.profile}
        rssi_threshold: {self.rssi_threshold}
        tx_power: {self.tx_power}
        up_time_sec: {self.up_time_sec}
        crc: {self.crc}
        """


def verify_crc(reported: int, data: bytes) -> bool:
    cr = crcmod.predefined.Crc("kermit")
    cr.update(data)
    return reported == cr.crcValue


class CtLogHeader():
    def __init__(self, data: bytes):
        if not self.verify_crc(data):
            raise ValueError("CRC check error")
        if len(data) != 49:
            raise ValueError("CT header input is the wrong length")

        self.ct_1 = LogCtHeaderP1(data[0:24])
        self.ct_2 = LogCtHeaderP2(data[24:50])

    def serialize(self, indent=None) -> str:
        return json.dumps(self.__dict__,
                          default=lambda o: o.__dict__,
                          indent=indent)

    def __repr__(self) -> str:
        return f"{self.ct_1} \n{self.ct_2}"

    def verify_crc(self, data: bytes) -> bool:
        reported = int.from_bytes(data[47:49],
                                  byteorder="little",
                                  signed=False)

        return verify_crc(reported, data[:47])

    def get_publish_hdr(self) -> bytes:
        return (struct.pack('<H', self.ct_1.entry_protocol_version) +
            binascii.unhexlify(self.ct_1.device_id) +
            struct.pack('<II', int(time.time()), self.ct_1.last_upload) +
            binascii.unhexlify(self.ct_2.fw_version) +
            struct.pack('<BH', self.ct_2.battery_level, self.ct_2.network_id))

class EntryHeader():
    def __init__(self, data: bytes, file_index: int):
        if len(data) != 16:
            raise ValueError("length of LogEntry should be 16 bytes")
        if (data[0]) != 165:
            print(binascii.hexlify(data))
            raise ValueError(
                f"For EntryHeader expected 0xA5, recieved {hex(data[0])}  @ index {hex(file_index)}"
            )

        self.flags = int.from_bytes(data[1:2],
                                    byteorder="little",
                                    signed=False)
        self.scan_interval = int.from_bytes(data[2:4],
                                            byteorder="little",
                                            signed=False)
        self.remote_device = str_end_rev(str(data[4:10].hex()))
        self.timestamp = int.from_bytes(data[10:14],
                                        byteorder="little",
                                        signed=False)
        self.length = int.from_bytes(data[14:16],
                                     byteorder="little",
                                     signed=False)

    def serialize(self, indent=None) -> str:
        return json.dumps(self.__dict__,
                          default=lambda o: o.__dict__,
                          indent=indent)

    def __repr__(self) -> str:
        return f"""Log Entry ->
        flags: {self.flags}
        scan_interval: {self.scan_interval}
        remote : {self.remote_device}
        timestamp : {self.timestamp}"""


class RssiTracking():
    """ base class for Record data using struct """
    def __init__(self, data: bytes):
        if len(data) != 8:
            raise ValueError(
                f"RssiTracking class initilized with 8 bytes, not {len(data)}")
        if data[0] != 17:
            raise ValueError(f"RssiTracking type = 0x11, not {data[0]}")
        (self.type, self.status, self.r1, self.scanIntOff, self.rssi,
         self.motion, self.txPower) = struct.unpack("<BBBHbBB", data)

    def serialize(self, indent=None) -> str:
        return json.dumps(self.__dict__,
                          default=lambda o: o.__dict__,
                          indent=indent)

    def __repr__(self) -> str:
        return self.serialize(indent=2)


class RssiTracking2():
    """ base class for Record data - this uses int.form bytes, not struct"""
    def __init__(self, data: bytes):
        if len(data) != 8:
            raise ValueError(
                f"RssiTracking class initilized with 8 bytes, not {len(data)}")
        if data[0] != 17:
            raise ValueError(f"RssiTracking type = 0x11, not {data[0]}")

        self.type = data[0]
        self.status = data[1],
        self.r1 = data[2]
        self.scanIntOff = int.from_bytes(data[3:5],
                                         byteorder="little",
                                         signed=False)

        self.rssi = int.from_bytes(data[5:6], byteorder="little", signed=True)
        self.motion = data[6]
        self.txPower = data[7]

    def serialize(self, indent=None) -> str:
        return json.dumps(self.__dict__,
                          default=lambda o: o.__dict__,
                          indent=indent)

    def __repr__(self) -> str:
        return self.serialize(indent=4)


CT_LOG_HEADER_SIZE = 49
ENTRY_HEADER_SIZE = 16
CT_RECORD_TYPE = 17
CT_RECORD_SIZE = 8


class Entry():
    def __init__(self, data: bytes, global_index: int):
        if len(data) < ENTRY_HEADER_SIZE:
            raise ValueError(
                f"entry data size errror @{global_index}: data entry must be greater than entry header size"
            )
        self.entry_header = EntryHeader(data[:ENTRY_HEADER_SIZE], global_index)
        self.records = []
        entry_size = self.entry_header.length
        i = ENTRY_HEADER_SIZE
        global_index += ENTRY_HEADER_SIZE
        #Verify CRC
        reported_crc = int.from_bytes(data[entry_size:entry_size + 2],
                                      byteorder="little",
                                      signed=False)
        if not verify_crc(reported_crc, data[:entry_size]):
            print(f"crc error {reported_crc} ")
            self._ret_offset = entry_size + 2
            return

        #TODO need to handle more than jsut type 17
        while i < entry_size:
            if data[i] != CT_RECORD_TYPE:
                logger.error(f"unknown record type {data[i]}")
            else:
                self.records.append(RssiTracking(data[i:i + CT_RECORD_SIZE]))
            i += CT_RECORD_SIZE
            global_index += CT_RECORD_SIZE
        self._ret_offset = i + 2

    def get_offset(self):
        return self._ret_offset

    def serialize(self, indent=None) -> str:
        return json.dumps(
            {
                "enytr_header": self.entry_header,
                "records": self.records
            },
            default=lambda o: o.__dict__,
            indent=indent)


CT_LOG_HEADER_SIZE = 49


class DataLog():
    def __init__(self, data: bytes):
        if len(data) < CT_LOG_HEADER_SIZE:
            raise ValueError("data size must be greater than header size")
        self.header = CtLogHeader(data[:CT_LOG_HEADER_SIZE])
        self.entries = []
        self.entry_data = data[CT_LOG_HEADER_SIZE:]
        i = 0
        file_index = CT_LOG_HEADER_SIZE
        while i < len(self.entry_data):
            ent = Entry(self.entry_data[i:], file_index)
            i += ent.get_offset()
            file_index = i + CT_LOG_HEADER_SIZE
            self.entries.append(ent)

    def serialize(self, indent=None) -> str:
        return json.dumps(self, cls=JsonEncoder, indent=indent)

    def encode_mg100(self) -> bytes:
        return self.header.get_publish_hdr() + self.entry_data

class JsonEncoder(json.JSONEncoder):
    """ custom JSON encoder for DataLog  """
    def default(self, obj):
        if isinstance(obj, Entry):
            return {"header": obj.entry_header, "records": obj.records}
        return obj.__dict__
