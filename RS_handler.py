from time import sleep

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QTime, pyqtSlot, QIODevice, QThread, QByteArray, QEventLoop
from PyQt5.QtWidgets import QRadioButton
import serial
import json
from queue import Queue

from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtWidgets import QAbstractButton


#################################  Utils  #######################################################
class FaultsBuffer():
    def __init__(self, raw_buffer: list[str]):
        self.fault_code = int(raw_buffer[0], 16)
        self.internal_flight_leg = (int(raw_buffer[1], 16) & 0x00FF) | (int(raw_buffer[2], 16) & 0x00FF) << 8
        self.internal_flight_mode = int(raw_buffer[3], 16)
        self.intermittent_count = int(raw_buffer[4], 16)
        self.flight_phase = int(raw_buffer[5], 16)
        self.ac_id = ''
        for i in range(7):
            self.ac_id += bytes.fromhex(raw_buffer[6+i]).decode('ascii')
        self.flight_num = ''
        for i in range(8):
            self.flight_num += bytes.fromhex(raw_buffer[13+i]).decode('utf-8')
        self.time = f'{int(raw_buffer[21])}:{int(raw_buffer[22][-1:] + raw_buffer[23][:-1])}:{60 * (int(raw_buffer[23][-1:])/10)}' # PAGE 1031
        self.date = f'{int(raw_buffer[24])}.{int(raw_buffer[25])}.{int(raw_buffer[26])}'
        self.internal_lru_num = int(raw_buffer[27], 16)
        matrix_bytes = raw_buffer[28:40]
        self.fault_matrix = int("".join(reversed(matrix_bytes)), 16)
        self.failure_class = int(raw_buffer[40], 16)

    def __str__(self):
        lines = []
        for key, value in self.__dict__.items():
            name = key.replace('_', ' ').capitalize()
            lines.append(f"{name}: {value}")
        return "\n".join(lines)

def _calculate_checksum(message: str) -> str:
    sum_int = 0
    for b in message.encode('ascii'):
        sum_int += b
    checksum = f'{sum_int & 0xFF:02X}'
    return checksum

def _validate_checksum(message: bytes) -> bool:
    try:
        received_checksum = int(message[-2:], 16)
        calculated_checksum = int(_calculate_checksum(message[:-2].decode('ascii')), 16)
        return received_checksum == calculated_checksum
    except Exception as e:
        print(e)
        return False

PSI_HPA = 68.9475729318 # 1 psi = 68.9475729318 hPa

MESSAGE_LENGTH = {
            ord('P'): 11,
            ord('T'): 5,
            ord('U'): 7,
            ord('V'): 5,
            ord('W'): 7,
            ord('Z'): 1
}

def _make_read_command(command_symb: str, address: int) -> str:
    addr_part: str = f'{address & 0xFF:02X}{(address >> 8) & 0xFF:02X}'
    command_without_sum: str = f'{command_symb}{addr_part}'
    full_command: str = f'{command_without_sum}{_calculate_checksum(command_without_sum)}'
    return full_command

def _make_write_command(command_symb: str, address: int, data: int) -> str:
    addr_part: str = f'{address & 0xFF:02X}{(address >> 8) & 0xFF:02X}'
    if command_symb == 'M': # byte
        data_part: str = f'{data & 0xFF:02X}'
    else: # word ('N')
        data_part: str = f'{data & 0xFF:02X}{(data >> 8) & 0xFF:02X}'
    command_without_sum: str = f'{command_symb}{addr_part}{data_part}'
    full_command: str = f'{command_without_sum}{_calculate_checksum(command_without_sum)}'
    return full_command

def make_read_byte_command(address: int) -> str:
    return _make_read_command('K', address)

def make_read_word_command(address: int) -> str:
    return _make_read_command('L', address)

def make_write_byte_command(address: int, byte: int) -> str:
    return _make_write_command('M', address, byte)

def make_write_word_command(address: int, word: int) -> str:
    return _make_write_command('N', address, word)

def _encode_ofv_status_packet(motor_state: bool, flag_bite_error_state: bool, position: int) -> bytes:
    id = 'S'
    # STATE -  motor powered operational (02H), motor not powered standby (01H), default: operational
    if motor_state:
        state = '02'
    else:
        state = '01'

    # FLT_MX - No faults; CAB_PRESSURE_SWITCH_ACTUATED = 0
    if flag_bite_error_state:
        bite = 'FFFFFFFF'
    else:
        bite = '00000000'

    # The conversion from encoded sensed position into degrees is: “convert hexadecimal number into decimal number and divide the decimal
    # number by 256 decimal”
    position = (position & 0xFFFF) * 256
    sended_position = f'{position & 0xFF:02X}{(position >> 8) & 0xFF:02X}'
    packet_raw = f'{id}{state}{bite}{sended_position}'
    full_packet = f'{packet_raw}{_calculate_checksum(packet_raw)}'
    return full_packet.encode('ascii')

############################################################################################################

class RWTask():
    def __init__(self, type: str, addr: int = 0, data: bytes = 0, timeout: int = 10, name: str = ''):
        self.type = type
        self.addr = addr
        self.data = data
        self.timeout = timeout
        self.name = name
        self.result = None
        self.loop = None

class RWHandler(QObject):
    sig_timers_start = pyqtSignal()
    sig_response_received = pyqtSignal(bytes)
    sig_request = pyqtSignal(object)
    sig_timeout = pyqtSignal()
    sig_timeout_start = pyqtSignal(int)
    sig_normal_resp = pyqtSignal(tuple)

    REPLY_BY_REQUEST = {
        'K': 'T',
        'L': 'U',
        'M': 'V',
        'N': 'W',
    }

    def __init__(self):
        super(RWHandler, self).__init__()

        self.port = QSerialPort(self)

        with open('ports.json', 'r', encoding='utf-8') as f:
            ports = json.load(f)

        self.port.setPortName(ports.get('rs-422'))
        self.port.setBaudRate(9600)

        self.buffer = bytearray()
        self.received_data: object = None

        #For request commands
        self.task_queue = Queue()
        self.current_task = None
        self.busy = False
        self.timeout_occurred = False

        #For normal message
        self.normal_task: RWTask = None

        #Timers
        self.timer_normal_message = QTimer(self)
        self.timer_normal_message.setInterval(200)

        self.timer_timeout = QTimer(self)
        self.timer_timeout.setSingleShot(True)

        # Connections
        self.port.readyRead.connect(self.ready_read)
        self.timer_normal_message.timeout.connect(self.slot_normal_op)
        self.sig_timers_start.connect(self.timer_normal_message.start)
        self.sig_timeout_start.connect(self.timer_timeout.start)
        self.timer_timeout.timeout.connect(self.on_timeout)

### Protocol ###
    def decode_commanded_pos_from_uut(self, raw_data: bytearray):
        decoded_data: str = raw_data.decode('ascii')
        br_raw: int = int(f'{decoded_data[3:5]}{decoded_data[1:3]}', 16)
        zc_raw: int = int(f'{decoded_data[7:9]}{decoded_data[5:7]}', 16)
        br = int(br_raw/256)
        zc = int(zc_raw/256)
        if br > 127: br -= 256
        if zc > 127: zc -= 256
        self.sig_normal_resp.emit((br, zc))

    def decode_rw_byte_reply(self, raw_data: str):
        return raw_data[1:3]

    def decode_rw_word_reply(self, raw_data: str):
        return f'{raw_data[3:5]}{raw_data[1:3]}'

    def decode_rw_reply(self, packet_str: str):
        if packet_str[0] in ('T', 'V'):
            return self.decode_rw_byte_reply(packet_str)
        return self.decode_rw_word_reply(packet_str)

    def handle_rw_reply(self, packet_str: str):
        if self.current_task is None:
            print(f'Dropped unexpected RS reply without active task: {packet_str}')
            return

        reply_type = packet_str[0]
        expected_reply_type = self.REPLY_BY_REQUEST.get(self.current_task.type)
        if reply_type != expected_reply_type:
            print(
                f'Dropped RS reply {reply_type} while waiting for '
                f'{expected_reply_type}: {packet_str}'
            )
            return

        self._finish_current_task(self.decode_rw_reply(packet_str))

    def message_route(self, packets):
        for packet in packets:
            packet_str = packet.decode('ascii')
            match (packet_str[0:1]):
                case 'P':
                    self.decode_commanded_pos_from_uut(packet)  # Identifies this as COMMANDED Position
                case 'T' | 'U' | 'V' | 'W':
                    self.handle_rw_reply(packet_str)
                case 'Z':
                    print('Z')

    @pyqtSlot()
    def ready_read(self):
        data= self.port.readAll()
        if data.isEmpty():
            return

        self.buffer.extend(data)

        buf = self.buffer
        n = len(buf)
        i = 0
        packets = []
        while i < n:
            b0 = buf[i]

            if b0 == ord('Z'):
                i += 1
                continue

            length = MESSAGE_LENGTH.get(b0)
            if length is None:
                i += 1
                continue

            if length == 0:
                i += 1
                continue

            if i + length > n:
                break

            packet = buf[i:i + length]

            if _validate_checksum(packet):
                packets.append(packet)
                i += length
            else:
                i += 1

        del buf[:i]
        self.message_route(packets)

    def start(self):
        if not self.open():

            return
        self.sig_timers_start.emit()

    def open(self) -> bool:
        if not self.port.open(QIODevice.OpenMode(QIODevice.ReadWrite)):
            print(f"Cannot open port: {self.port.portName()}")
            return False

        print(f"RS port {self.port.portName()} opened successfully")
        return True

    def set_normal_task(self, task: RWTask):
        self.normal_task = task

    @pyqtSlot()
    def slot_normal_op(self):
        if self.normal_task is None or self.busy:
            return
        self.port.write(self.normal_task.data)

    def _clear_input(self):
        self.buffer.clear()
        self.received_data = None
        if self.port.isOpen():
            input_direction = getattr(QSerialPort, 'Input', None)
            if input_direction is None:
                self.port.clear()
            else:
                self.port.clear(input_direction)

    def _process_next_task(self):
        if self.current_task is not None or self.task_queue.empty():
            return

        self.current_task = self.task_queue.get()
        self.busy = True
        self.timeout_occurred = False
        self._clear_input()
        self.timer_timeout.start(self.current_task.timeout)
        self.port.write(self.current_task.data)
        self.port.flush()

    def _finish_current_task(self, result):
        task = self.current_task
        if task is None:
            return

        self.timer_timeout.stop()
        task.result = result
        self.current_task = None
        self.busy = False

        if task.loop is not None and task.loop.isRunning():
            task.loop.quit()

        QTimer.singleShot(0, self._process_next_task)

    def _do_task(self, task: RWTask) -> object:
        task.loop = QEventLoop()
        self.task_queue.put(task)
        self._process_next_task()
        task.loop.exec_()
        return task.result

    def read_byte(self, addr):
        command = make_read_byte_command(addr).encode('ascii')
        return self._do_task(RWTask('K', addr, command, timeout=1000))

    def read_word(self, addr):
        command = make_read_word_command(addr).encode('ascii')
        return self._do_task(RWTask('L', addr, command, timeout=1000))

    def write_byte(self, addr, data):
        command = make_write_byte_command(addr, data).encode('ascii')
        return self._do_task(RWTask('M', addr, command, timeout=1000))

    def write_word(self, addr, data):
        command = make_write_word_command(addr, data).encode('ascii')
        return self._do_task(RWTask('N', addr, command, timeout=1000))

    @pyqtSlot()
    def on_timeout(self):
        """Обработчик таймаута"""
        self.timeout_occurred = True
        if self.current_task is None:
            return
        print(f'Timeout occurred in task with command: {self.current_task.data}')
        self._clear_input()
        self._finish_current_task(None)


class RsWorker(QObject):
    signal_pc_alt = pyqtSignal(tuple)
    sig_send_consts = pyqtSignal(dict)
    sig_rw_reply = pyqtSignal(int, str)
    sig_show_fbuffs = pyqtSignal(list)
    sig_progress_read_buffs = pyqtSignal(int)
    sig_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.handler = RWHandler()
        self.handler.setParent(self)

        self.timer_poll = QTimer(self)
        self.timer_poll.setInterval(200)
        self.timer_poll.timeout.connect(self.on_timer_poll)
        self.handler.sig_timers_start.connect(self.timer_poll.start)
        self.is_polling = False

        self.raw_buffs = []

        self.consts = None

        self.flag_activity_rs_communication = False

        self.pc_avg = []
        self.alt_avg = []

    @pyqtSlot()
    def start(self):
        self.handler.start()

    def read_pc_alt_raw(self):
        pc, alt = None, None
        while pc is None or alt is None:
            pc = self.handler.read_word(0xA004)
            alt = self.handler.read_word(0xA01E)
        return pc, alt

    def read_pc_alt(self):
        pc = self.handler.read_word(0xA004)
        if pc is None:
            return
        pc = (int(pc, 16) / 1024) * PSI_HPA
        self.pc_avg.append(pc)
        if len(self.pc_avg) > 25:
            self.pc_avg.pop(0)
        pc_res = str(round(sum(self.pc_avg) / len(self.pc_avg), 2))

        alt = self.handler.read_word(0xA01E)
        if alt is None:
            return
        alt = int(alt, 16)
        if alt < 32768:
            alt = alt / 4
        else:
            alt = round(((65535 - alt) / -4), 2)

        self.alt_avg.append(alt)
        if len(self.alt_avg) > 25:
            self.alt_avg.pop(0)
        alt_res = str(round(sum(self.alt_avg) / len(self.alt_avg), 2))

        self.signal_pc_alt.emit((pc_res, alt_res))


    def read_pn_hw(self):
        hw = '0000-'
        for i in range(0, 8):
            dat = self.handler.read_byte(0xA065 + i)
            if dat is None: return
            dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            hw += dat
        return hw

    def read_pn_sw(self):
        sw = ''
        for i in range(0, 2):
            dat = self.handler.read_byte(0x1000 + i)
            if dat is None: return
            dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            sw += dat
        return sw

    def read_sw_ver(self):
        sw_ver = ''
        for i in range(0, 2):
            dat = self.handler.read_byte(0x1010 + i)
            if dat is None: return
            dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            sw_ver += dat
        return sw_ver

    def read_sn(self):
        sn = ''
        for i in range(0, 7):
            dat = self.handler.read_byte(0xA070 + i)
            if dat is None: return
            dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            sn += dat
        print(f'SN: {sn}')
        return sn

    def read_fault_buffer(self, n: int) -> list[str]:
        buffer = []
        for base in range(0xB001, 0xB02A):
            addr = base + n * 0x29
            data_byte = self.handler.read_byte(addr)
            buffer.append(data_byte)
        return buffer

    @pyqtSlot()
    def slot_get_consts(self):
        pc, alt_cab_rato = self.read_pc_alt_raw()
        # 'pc_offset_nvm': int(self.handler.read_word(0xA100) / 2048) * PSI_HPA,
        # 'pc_offset_nvm_checksum': (int(self.handler.read_word(0xA102), 16) / 2048) * PSI_HPA,
        # 'pc_check_offst': (int(self.handler.read_word(0xA104), 16) / 2048) * PSI_HPA,
        # 'drift_comp_cnt': int((self.handler.read_word(0xA106) + self.handler.read_word(0xA108)), 16),
        # 'pc_offset_fail_cnt': int(self.handler.read_byte(0xA10A), 16),
        self.consts = {
            'pc_offset_nvm' : self.handler.read_word(0xA100),
            'pc_offset_nvm_checksum' : self.handler.read_word(0xA102),
            'pc_check_offst' : self.handler.read_word(0xA104),
            'drift_comp_cnt_0' : self.handler.read_word(0xA106),
            'drift_comp_cnt_1': self.handler.read_word(0xA108),
            'pc_offset_fail_cnt' : self.handler.read_byte(0xA10A),
            'pn_hw': self.read_pn_hw(),
            'pn_sw': self.read_pn_sw(),
            'sn': self.read_sn(),
            'sw_ver': self.read_sw_ver(),
            'pc': pc,
            'alt_cab_rato': alt_cab_rato,
        }
        self.sig_send_consts.emit(self.consts)


    @pyqtSlot(bool, int)
    def slot_read(self, state, addr):
        if state:
            reply = self.handler.read_byte(addr)
        else:
            reply = self.handler.read_word(addr)
        self.sig_rw_reply.emit(0, reply or '')

    @pyqtSlot(bool, int, int)
    def slot_write(self, state, addr, data):
        if state:
            reply = self.handler.write_byte(addr, data)
        else:
            reply = self.handler.write_word(addr, data)
        self.sig_rw_reply.emit(1, reply or '')

    @pyqtSlot(bool, bool, int)
    def slot_bite_change(self, state, bite_fault_flag, position):
        self.handler.set_normal_task(RWTask('S', data=_encode_ofv_status_packet(
            motor_state=state,
            flag_bite_error_state=bite_fault_flag,
            position=position)))

    @pyqtSlot()
    def on_timer_poll(self):
        if self.handler.busy or self.is_polling:
            return
        self.is_polling = True
        self.read_pc_alt()
        self.is_polling = False

    @pyqtSlot()
    def test(self):
        pass

    @pyqtSlot()
    def read_fbuffs(self):
        self.slot_get_consts()
        fbuffs = []
        progress: int = 0
        self.sig_progress_read_buffs.emit(progress)
        for n in range(0, 32):
            raw = self.read_fault_buffer(n)
            self.raw_buffs.extend(raw)
            fbuffs.append(FaultsBuffer(raw))
            progress += 3
            self.sig_progress_read_buffs.emit(progress)
        self.sig_progress_read_buffs.emit(100)
        self.sig_show_fbuffs.emit(fbuffs)



