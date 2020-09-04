#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import re
import logging
import binascii
from collections import namedtuple
from typing import Tuple
logger = logging.getLogger(__name__)


def writec_resp(resp) -> int:
    conn_str: str = resp.split(":")[1]
    res = re.match("0{3}\dF{2}", conn_str)
    if res:
        return int(res.group(0)[3])
    return -1


def get_handle_from_conn_resp(resp: str) -> str:
    ''' return connection handle, or None  '''
    if resp == "dconnTO\n":
        return
    try:
        data = resp.split(" ")
        if data[0].startswith("writec:"):
            return data[0].split(":")[1]
        return

    except Exception:
        logger.error(" -> could not hanlde {}".format(repr(resp)))
        return


bt_resp = namedtuple('bt_response', ['mac', 'handle'])


def dconn_resp(resp: str, last: str) -> bt_resp:
    l_resp = resp.split(" ")
    mac = l_resp[0].split(":")[1]
    return bt_resp(mac, l_resp[1].replace("\n", ""))


def mac_parse(resp: str, last: str) -> bt_resp:
    if ":" in resp:
        conn_str: str = resp.split(":")[1]
        match = re.match("[A-Fa-f0-9]{14}", conn_str)
        if match:
            return bt_resp(match.group(0), None)
    return


def handle_parse(resp: str, last: str) -> bt_resp:
    if ":" in resp:
        conn_str: str = resp.split(":")[1]
        match = re.match("[A-Fa-f0-9]{8}", conn_str)
        if match:
            return bt_resp(None, match.group(0))
    return


def handle_parse_last(resp: str, last: str) -> bt_resp:
    if ":" in resp:
        conn_str: str = resp.split(":")[1]
        match = re.match("[A-Fa-f0-9]{8}", conn_str)
        if match:
            return bt_resp(last, match.group(0))
    return


sb_conn_resp = {
    "con": mac_parse,
    "dCon": mac_parse,
    "evt_hvx": handle_parse,
    "connA": dconn_resp,
    "dconnH": handle_parse,
    "writec": handle_parse_last
}


def handle_resp(resp: str, last: str) -> str:
    ''' return handle of connection, 0 for timeout.  '''

    data = resp.split(" ")
    if len(data) > 1:
        prefix = data[0].split(":")[0]
        return sb_conn_resp[prefix](resp, last)
    else:
        if data == ["dconnTO\n"]:
            return bt_resp(last, None)


def time_out() -> str:
    return 'dconnTO\n'


class SbDecodeError(Exception):
    pass


def sb_notif_decode(data: str) -> Tuple[str, int, bytes]:
    try:
        if not data.startswith("evt_hvx:"):
            raise SbDecodeError
        temp = data.split(' ')
        if len(temp) != 3:
            raise SbDecodeError
        return temp[0].split(":")[1], temp[1], binascii.unhexlify(
            temp[2].replace("\n", ""))
    except Exception as ex:
        print(ex)
        raise SbDecodeError
