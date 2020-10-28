#
# copyright (c) 2020 Laird Connectivity
#
# SPDX-License-Identifier: Apache-2.0
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License
# for the specific language governing permissions and limitations
# under the License.
import re
import time
import glob
import logging
import serial
from functools import partial

logger = logging.getLogger(__name__)

def startup(port, app, folder, cmds):
    with BTManager(port) as bt:
        bl654_hex = ""
        startup = {"port": port, "SB app": app}

        res = bt.get_sb_firmware()
        if res:
            startup["firmware_version"] = res

        res = bt.get_sb_version()
        if res:
            bl654_hex = res.replace(" ", "_")
            startup["hex"] = res

        for cmd in cmds:
            resp = bt.at_command(cmd)
            if not resp.startswith('\n00'):
                logger.warning('AT command response: {}'.format(resp))

        logger.info(startup)
        try:
            bt.test_start_app(app)
        except SmartBasicException as sb:
            app_startup_error_handle(bt, sb, bl654_hex, app, folder)
            bt.test_start_app(app)


def strip_extra_characters(str):
    str = re.sub('\d+\t', "", str)
    str = re.sub('[\r"0"]', "", str)
    return str


def generic_handler(cmd, err):
    pass


def str_to_bytes(my_str):
    return bytes(my_str, "ascii")


READ_DIR = b"at+dir \r\n"
RESET = b'atz \r\n'
FILE_CLOSE = b'at+fcl \r\n'
SB_VERSION = b"ati 13 \r\n"
SB_FIRMWARE = b"ati 3 \r\n"


def try_decode_ret(response):
    logger.debug(response)
    try:
        str_res = response.decode("ascii").strip("\n")
        logger.debug(str_res)
        return str_res.split("\t")[-1].strip("\r")
    except Exception as e:
        logger.error("response handling error {} ".format(e))


class SmartBasicException(Exception):
    def __init__(self, message):
        super().__init__(message)


class BTManager():
    def __enter__(self):
        return self

    def __init__(self, port):

        logger.info(("Running with port: {}".format(port)))
        self.sp = serial.Serial(port,
                                115200,
                                timeout=1,
                                parity=serial.PARITY_NONE,
                                rtscts=1)
        self.sp.send_break(duration=0.020)
        self.sp.reset_input_buffer()
        logger.info("port initialized")

    def __exit__(self, type, value, traceback):
        self.sp.close()

    def get_sb_version(self):
        res = self.write_bytes(SB_VERSION)
        self.sp.read_until(b"\r")
        return try_decode_ret(res).strip(" ")

    def get_sb_firmware(self):
        res = self.write_bytes(SB_FIRMWARE)
        self.sp.read_until(b"\r")
        return try_decode_ret(res)

    def write_str(self, cmd):
        return self.write_bytes(str_to_bytes(cmd))

    def write_bytes(self, bcmd):
        self.sp.write(bcmd)
        self.sp.flush()
        return self.sp.read_until(b'\r', 100)

    def send_single_cmd(self, cmd, meta, handler):
        cmd_line = cmd + ' ' + meta + '\r'
        logger.debug(("sending single command {}".format(repr(cmd_line))))
        res = self.write_str(cmd_line)
        if b'01\t' not in res:
            return (True, "")
        else:
            err_string = handler(cmd, res)
        return (False, err_string)

    def reset(self):
        return self.write_bytes(RESET)

    def read_dir(self):
        self.sp.write(READ_DIR)
        self.sp.flush()
        res = self.sp.read_until('00\r')
        logger.info("res {}".format(repr(res)))
        if b'\n01' in res:
            return (False, res)
        #read again
        self.sp.read_until(b"\r", 10)
        logger.debug(res)
        res_str = res.decode('utf-8')
        res = res_str.split('\n')
        res = list(map(strip_extra_characters, res))
        return (True, list([x for x in res if x != '']))

    def del_file(self, name):
        return self.send_single_cmd('at+del', '"{}"'.format(name),
                                    generic_handler)

    def load_file(self, name, file):
        logger.info(("file to load {} with name {}".format(file, name)))
        try:
            with open(file, 'rb') as f:
                self.write_bytes(RESET)
                fowcmd = 'at+fow \"' + name + '\"\r\n'
                res = self.write_str(fowcmd)
                logger.info(("open file response: {}".format(repr(res))))
                if b'01\t' in res:
                    return False
                for block in iter(partial(f.read, 100), b''):
                    str_block = block.hex()
                    strblock = 'at+fwrh \"' + str_block + '\"\r\n'
                    logger.debug(("write chunk {}".format(repr(str_block))))
                    res = self.write_str(strblock)
                    logger.debug(("write chunk response {}".format(repr(res))))
                    if b'01\t' in res:
                        return False
                res = self.write_bytes(FILE_CLOSE)
                logger.debug(res)
                return res

        except IOError as e:
            logger.error(e)

    def at_command(self, cmd, timeout=2):
        logger.info(("at cmd:{}".format(cmd)))
        cmd = cmd + "\r"
        self.sp.timeout = timeout
        self.sp.write(str_to_bytes(cmd))
        self.sp.flush()
        res = self.sp.read_until('\r'.encode())
        logger.debug(("response raw:{}".format(repr(res))))
        return res.decode("utf-8")

    def test_start_app(self, cmd):
        logger.info(("starting app:{}".format(cmd)))
        res = self.at_command('at+run \"' + cmd + "\"")
        logger.info('App start response: {}'.format(res))
        if not res.startswith("\n01"):
            return
        err = res.split("\t")[1].strip("\r")
        raise SmartBasicException(err)

def find_app_file(path, app, hex):
    search = path + app + "*"
    logger.debug("searching   {}".format(search))
    files = glob.glob(search)
    logger.debug("found files {}".format(files))
    for file in files:
        if hex in file:
            return file


def app_startup_error_handle(bt, sb, bl654_hex_str, app_name, file_path):
    logger.error("smartBasic exception {}".format(sb))
    if str(sb) == '070C' or str(sb) == '180E':
        logger.info("flash reset")
        bt.write_str("at&f 1 \r\n")
        time.sleep(1.9)
        res = bt.sp.read_until(b"\r", 200)
        logger.info(res.decode("utf-8").strip('\n'))
    else:
        logger.error(sb)
    file = find_app_file(file_path, app_name, bl654_hex_str)
    logger.info("loading file {}".format(file))
    if not file:
        raise Exception("unable to find suitable file")
    logger.info("could not start app")
    bt.load_file(app_name, file)
