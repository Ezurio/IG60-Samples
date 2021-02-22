#
# copyright (c) 2021 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
#
# This module creates a JSON payload (from the CtFile class)
# that exactly matches the output of the MG100 binary payload
# as decoded by the Lambda at edge

import binascii
import json
import struct

CT_ENTRY_HEADER_SIZE = 16
CT_ENTRY_LOG_SIZE = 8
CT_LOG_HEADER_SIZE = 49

class CtLog():
    def __init__(self, b):
        self.recordType, \
            status, \
            reserved1, \
            self.delta, \
            self.rssi, \
            self.motion, \
            self.txPower = struct.unpack('<BBBHbBb', b[:CT_ENTRY_LOG_SIZE])

class CtEntry():
    def __init__(self, b):
        self.entryStart, \
            self.flags, \
            self.scanInterval, \
            serial_bytes, \
            self.timestamp, \
            self.length = struct.unpack('<BBH6sIH', b[0:CT_ENTRY_HEADER_SIZE])
        # Reverse bytes & convert to hex string
        self.serial = binascii.hexlify(serial_bytes[::-1]).decode('utf-8')
        # Read log entries up to length in header
        self.logs = []
        log_offset = CT_ENTRY_HEADER_SIZE
        while log_offset < self.length and log_offset < len(b):
            ctlog = CtLog(b[log_offset:])
            log_offset = log_offset + CT_ENTRY_LOG_SIZE
            self.logs.append(ctlog)

    def getLen(self):
        return self.length + 2 # Add CRC length

class CtJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        return obj.__dict__

class CtFile():
    def __init__(self, b):
        self.entryProtocolVersion, \
            max_entry_size, \
            entry_count, \
            device_id_bytes, \
            self.deviceTime, \
            log_size, \
            self.lastUploadTime, \
            fw_version_bytes, \
            devices_seen, \
            self.networkId, \
            ad_interval_ms, \
            log_interval_min, \
            scan_interval_sec, \
            battery_level, \
            scan_duraction_sec, \
            profile, \
            rssi_threshold, \
            tx_power, \
            up_time_sec = struct.unpack('<HHH6sIII4sHHHHHBBBbbI', b[:CT_LOG_HEADER_SIZE-2])
        # Reverse bytes & convert to hex string
        self.deviceId = binascii.hexlify(device_id_bytes[::-1]).decode('utf-8')
        # Convert bytes to string
        self.fwVersion = binascii.hexlify(fw_version_bytes).decode('utf-8')
        # Scale battery level to mv
        self.batteryLevel = battery_level * 16
        # Read entries until no more data
        self.entries = []
        entry_offset = CT_LOG_HEADER_SIZE
        while entry_offset + CT_ENTRY_HEADER_SIZE <= len(b):
            entry = CtEntry(b[entry_offset:])
            self.entries.append(entry)
            entry_offset = entry_offset + entry.getLen()

    def serialize(self, indent=None):
        return json.dumps(self, cls=CtJsonEncoder, indent=indent)
