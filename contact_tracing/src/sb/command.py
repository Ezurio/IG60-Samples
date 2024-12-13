#
# copyright (c) 2024 Ezurio LLC.
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import binascii
import logging
logger = logging.getLogger(__name__)


def get_conn_cmd(mac: str,
                 conn_to_ms=250,
                 min_con_int_us=7500,
                 max_con_int_us=9000,
                 link_sup_timeout_us=4000000) -> bytes:
    resp = f'connect {mac} {conn_to_ms} {min_con_int_us} {max_con_int_us} {link_sup_timeout_us}  \r\n'
    return bytes(resp, 'ascii')


def advertise(adv: bytes) -> bytes:
    prefix = bytes(f"adv ", "ascii")
    postfix = bytes(f" \r\n", "ascii")
    return prefix + adv + postfix


def get_scan_cmd(timeout=300) -> bytes:
    return bytes("scan start {} 0 \r\n".format(timeout), "ascii")


def get_notify_enable_cmd(conn_handle: int) -> bytes:
    return bytes(f"gattc write {conn_handle} 19 010 \r\n", "ascii")


def get_params_cmd(conn_handle: int) -> bytes:
    return bytes(
        f"gattc writecmd {conn_handle} 18 0000001b00084200a2646e616d656f2f6c66732f706172616d732e747874636f666600 \r\n",
        "ascii")


def get_echo_cmd(conn_handle: int) -> bytes:
    return bytes(
        f"gattc writecmd {conn_handle} 18  0200000B00004200A161646774657374313233 \r\n",
        "ascii")


def get_disconnect_cmd(conn_handle: int) -> bytes:
    return bytes(f"disconnect {conn_handle} \r\n", "ascii")


BIN = True
LOG_CT = "/log/ct"
PARAMS = "/lfs/params.txt"

cmd_str = {
    LOG_CT:
    "0000001300084200a2646e616d65672f6c6f672f6374636f666600",
    PARAMS:
    "0000001b00084200a2646e616d656f2f6c66732f706172616d732e747874636f666600"
}

cmd_bin = {
    LOG_CT:
    binascii.unhexlify(
        b"0000001300084200a2646e616d65672f6c6f672f6374636f666600"),
    PARAMS:
    binascii.unhexlify(
        b"0000001b00084200a2646e616d656f2f6c66732f706172616d732e747874636f666600"
    )
}


def gattc_wrap(func):
    def wrapper(*args, **kwargs):
        conn_handle, data = func(*args, **kwargs)
        prefix = bytes(f"gattc writecmdx {conn_handle} {len(data)} ", "ascii")
        postfix = bytes(" \r\n", "ascii")
        return prefix + data + postfix

    return wrapper


def get_gattc_write(conn_handle: int, data: bytes) -> bytes:
    if BIN:
        prefix = bytes(f"gattc writecmdx {conn_handle} {len(data)} ", "ascii")
        postfix = bytes(" \r\n", "ascii")
        return prefix + data + postfix
    else:
        data_str = str(binascii.hexlify(data), "ascii")
        return bytes(f"gattc writecmd {conn_handle} 18 {data_str} \r\n",
                     "ascii")


def get_file(conn_handle: int, filename: str) -> bytes:
    if BIN:
        data = cmd_bin[filename]
        prefix = bytes(f"gattc writecmdx {conn_handle} {len(data)} ", "ascii")
        postfix = bytes(" \r\n", "ascii")
        return prefix + data + postfix

    else:
        data = cmd_str[filename]
        return bytes(f"gattc writecmd {conn_handle} 18 {data}\r\n", "ascii")
