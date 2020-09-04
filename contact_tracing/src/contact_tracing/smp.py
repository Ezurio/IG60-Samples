#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
from enum import Enum
from struct import pack, unpack
import cbor
import binascii
import logging
import time
import sb.command as bt
from typing import Tuple
logger = logging.getLogger(__name__)


class Op(Enum):
    '''enumeration of npm_op operation values '''
    MGMT_OP_READ = 0
    MGMT_OP_READ_RSP = 1
    MGMT_OP_WRITE = 2
    MGMT_OP_WRITE_RSP = 3


class Group(Enum):
    ''' first 64 groups are reserved for system level commands. Per-user commands 
    are defined after group 64 '''
    MGMT_GROUP_ID_OS = 0
    MGMT_GROUP_ID_IMAGE = 1
    MGMT_GROUP_ID_STAT = 2
    MGMT_GROUP_ID_CONFIG = 3
    MGMT_GROUP_ID_LOG = 4
    MGMT_GROUP_ID_CRASH = 5
    MGMT_GROUP_ID_SPLIT = 6
    MGMT_GROUP_ID_RUN = 7
    MGMT_GROUP_ID_FS = 8
    MGMT_GROUP_ID_SHELL = 9
    MGMT_GROUP_ID_PERUSER = 64


SMP_HEADER_SIZE = 8


class Smp(object):
    def __init__(self,
                 op_code: int,
                 data: bytes,
                 group: int,
                 seq=0,
                 flags=0,
                 id=0) -> None:
        self.op_code = op_code
        self.flags = flags
        self.group = group
        self.seq = seq
        self.id = id
        self.length: int = len(data)
        self.data = data

    def seralize(self) -> bytes:
        try:
            self.header = pack('>BBHHBB', self.op_code.value, self.flags,
                               self.length, self.group, self.seq, self.id)
            return self.header + self.data
        except Exception as e:
            logger.error(f"struct pack error smp serialize{e} {self.seq}")

    def __repr__(self) -> str:
        return "".join(["{:02x} ".format(i) for i in self.seralize()])


class EchoCmd(Smp):
    def __init__(self, data: str) -> None:
        self.req = {"d": data}
        self.data = cbor.dumps(self.req)
        super().__init__(Op.MGMT_OP_WRITE, self.data, 0)

    def dumps(self) -> bytes:
        return self.seralize()


class Download(Smp):
    def __init__(self, filename: str, off: int = 0, seq: int = 0) -> None:
        self.req = {"name": filename, "off": off}
        self.data = cbor.dumps(self.req)
        super().__init__(Op.MGMT_OP_READ, self.data,
                         Group.MGMT_GROUP_ID_FS.value, seq)

    def dumps(self) -> bytes:
        logger.debug(f" <- request:{self.req} sequence:{self.seq}")
        return self.seralize()


class SmpError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors


class SmpFileChunk():
    def __init__(self, mac, bheader: bytes):
        try:
            (_, _, self.length, _st, self.seq, _) = unpack('>BBHHBB', bheader)
        except Exception as e:
            logger.error(f"smp File Chunk {e}")
            raise SmpError("could not parse SMP file header", {})
        self.raw_data = b""
        self.cur_len = 0
        self.mac_addr = mac
        logger.debug(f"{self.mac_addr} new chunk -> len:{self.length}")

    def add_data(self, data: bytes) -> bool:
        self.raw_data += data
        self.cur_len += len(data)
        logger.debug(
            f"{self.mac_addr} chunk add data -> len:{self.length} current len: {self.cur_len} seq:{self.seq}  "
        )
        if self.cur_len == self.length:
            self._decode()
            return True
        return False

    def _decode(self):
        self.payload = cbor.loads(self.raw_data)
        if self.payload["rc"]:
            rc = self.payload["rc"]
            if rc != 0:
                logger.error(f"rc error{self.mac_addr}  -> {self.payload} ")
                self.is_complete = True
                raise SmpError(f"return code error", {"rc": rc})
        logger.debug(
            f"{self.mac_addr} chunk decode -> { [ k  for k in self.payload.items() if k[0] != 'data' ]}"
        )

    def is_complete(self) -> bool:
        return self.cur_len == self.length

    def __repr__(self) -> str:
        ret = f"chunk-> curlength :{self.cur_len}  length:{self.length}"
        ret += f" payload:{self.payload} "
        return ret


LOG_CT = "/log/ct"
PARAMS = "/lfs/params.txt"
cmd_bin = {
    LOG_CT: b'\x00\x00\x00\x13\x00\x08\x10\x00\xa2dnameg/log/ctcoff\x00',
    PARAMS:
    b'\x00\x00\x00\x1b\x00\x08\x00\x00\xa2dnameo/lfs/params.txtcoff\x00'
}


class SmpFileResp():
    def __init__(self, mac: str, file_name: str = "/lfs/params.txt"):
        self.file_name = file_name
        self.chunks = []
        self.seq = 0
        self.new = True
        self.cur_len = 0
        self.file_len = 0
        self.mac = mac
        self.complete = False
        self.start = time.time()
        super().__init__()

    def _decode(self) -> None:
        ret = b""
        for chunk in self.chunks:
            if chunk.payload["data"]:
                ret += chunk.payload["data"]
        return ret

    def _add_chunk(self, data: bytes):
        """ add the data to the current chunk """
        if self.new:
            self.cur_chunk = SmpFileChunk(self.mac, data[:SMP_HEADER_SIZE])
            self.cur_chunk.add_data(data[SMP_HEADER_SIZE:])
            self.seq = self.cur_chunk.seq
        else:
            self.cur_chunk.add_data(data)
        self.new = False

    def _get_total_length(self):
        """ The first Chunk shall contain the total length of the file """
        if self.file_len == 0:
            self.file_len = self.cur_chunk.payload["len"]

    def _complete_actions(self):
        """ When the complete file is received, take these actions """
        self.complete = True
        self.ret = self._decode()
        dur_ms = (time.time() - self.start) * 1000
        len_ret = len(self.ret)
        logger.info(
            f"smp download complete - duration(ms): {dur_ms : .3f}  length(B): {len_ret}  Bytes/sec: {len_ret/(dur_ms/1000) :.2f}"
        )

    def data(self, data: bytes) -> bool:
        try:
            self._add_chunk(data)
        except SmpError as e:
            logger.debug(f"except SmpError {e}")
            #for an rc error - just wrap things up and close the connection
            #is_complete should be true  - this is set by the chunk rc check
            self._complete_actions()
            return True

        if not self.cur_chunk.is_complete():
            return False

        self._get_total_length()
        if self.cur_chunk.payload['data']:
            self.cur_len += len(self.cur_chunk.payload['data'])
            logger.debug(
                f"smp decode - {[ k  for k in self.cur_chunk.payload.items() if k[0] != 'data' ]} :total_length {self.file_len} current length: {self.cur_len}"
            )
            self.chunks.append(self.cur_chunk)
        else:
            logger.error(f"unexpected chunk {self.cur_len.payload}")
        if self.cur_len == self.file_len:
            self._complete_actions()
        self.new = True
        return True

    def read(self) -> bytes:
        return self.ret

    def __repr__(self) -> str:
        ret = f"smp file  -> "
        ret += f"chunks :{self.chunks} "
        return ret

    def _seq_inc(self):
        if self.seq == 255:
            self.seq = 0
        else:
            self.seq += 1

    def _get_cbor_header(self) -> bytes:
        self._seq_inc()
        return Download(self.file_name, self.cur_len, self.seq).dumps()

    @bt.gattc_wrap
    def get_cmd(self, conn: str):
        return conn, self._get_cbor_header()

    def get_cbor_header_debug(self) -> str:
        ret = self.get_cbor_header()
        return "".join(["{:02x} ".format(i) for i in ret])

    def is_complete(self) -> bool:
        return self.complete

    @bt.gattc_wrap
    def get_file_cmd(self, conn: str):
        cmd = cmd_bin.get(self.file_name,
                          Download(self.file_name, 0, 0).seralize())
        return conn, cmd


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s  %(levelname)s  %(filename)s - %(message)s',
        level=logging.DEBUG)
