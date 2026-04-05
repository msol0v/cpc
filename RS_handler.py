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
    received_checksum = int(message[-2:], 16)
    calculated_checksum = int(_calculate_checksum(message[:-2].decode('ascii')), 16)
    return received_checksum == calculated_checksum

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

############################################################################################################

class RWTask():
    def __init__(self, type: str, addr: int = 0, data: bytes = 0, timeout: int = 10, name: str = ''):
        self.type = type
        self.addr = addr
        self.data = data
        self.timeout = timeout
        self.name = name

class RWHandler(QObject):
    sig_timers_start = pyqtSignal()
    sig_response_received = pyqtSignal(bytes)
    sig_request = pyqtSignal(object)
    sig_timeout = pyqtSignal()
    sig_timeout_start = pyqtSignal(int)
    sig_normal_resp = pyqtSignal(tuple)

    def __init__(self):
        super(RWHandler, self).__init__()

        self.port = QSerialPort()
        self.port.setPortName('COM12')
        self.port.setBaudRate(9600)

        self.buffer = bytearray()
        self.received_data: object = None

        #For request commands
        self.current_task = None
        self.busy = False
        self.timeout_occurred = False

        #For normal message
        self.normal_task: RWTask = None

        #Timers
        self.timer_normal_message = QTimer()
        self.timer_normal_message.setInterval(200)

        self.timer_request_commands = QTimer()
        self.timer_request_commands.setInterval(3)

        self.timer_timeout = QTimer()
        self.timer_timeout.setSingleShot(True)

        # Connections
        self.port.readyRead.connect(self.ready_read)
        self.timer_normal_message.timeout.connect(self.slot_normal_op)
        self.timer_request_commands.timeout.connect(self.slot_request_op)
        self.sig_timers_start.connect(self.timer_normal_message.start)
        self.sig_timers_start.connect(self.timer_request_commands.start)
        self.sig_timeout_start.connect(self.timer_timeout.start)
        self.timer_timeout.timeout.connect(self.on_timeout)
        self.sig_request.connect(self.request_to_buf)

### Protocol ###
    def decode_commanded_pos_from_uut(self, raw_data: bytes):
        #br = int(f'{raw_data[3:5]}{raw_data[1:3]}', 16)
        #zc = int(f'{raw_data[7:9]}{raw_data[5:7]}', 16)
        br = int(raw_data[1:5], 16).to_bytes(2, byteorder='big').decode('ascii')
        zc = int(raw_data[5:9], 16).to_bytes(2, byteorder='big').decode('ascii')
        self.sig_normal_resp.emit((br, zc))

    def decode_rw_byte_reply(self, raw_data: str):
        data = raw_data[1:3]
        self.sig_request.emit(data)

    def decode_rw_word_reply(self, raw_data: str):
        data = f'{raw_data[3:5]}{raw_data[1:3]}'
        self.sig_request.emit(data)

    def message_route(self, packets):
        for packet in packets:
            packet_str = packet.decode('ascii')
            match (packet_str[0:1]):
                case 'P':
                    self.decode_commanded_pos_from_uut(packet)  # Identifies this as COMMANDED Position
                case 'T':
                    self.decode_rw_byte_reply(packet_str)  # Identifies this as READ BYTE REPLY message
                case 'U':
                    self.decode_rw_word_reply(packet_str)  # Identifies this as READ WORD REPLY message
                case 'V':
                    self.decode_rw_byte_reply(packet_str)  # Identifies this as WRITE BYTE REPLY message
                case 'W':
                    self.decode_rw_word_reply(packet_str)  # Identifies this as WRITE WORD REPLY message
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
            if packet != b'Z':
                if _validate_checksum(packet):
                    packets.append(packet)
            else: packets.append(packet)
            i += length

        del buf[:i]
        self.message_route(packets)

    @pyqtSlot(bytes)
    def request_to_buf(self, data: object):
        self.received_data = data

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
        if self.normal_task is None:
            return
        self.port.write(self.normal_task.data)

    @pyqtSlot()
    def slot_request_op(self):
        if self.current_task is None or self.busy:
            return

        self.busy = True
        self.port.write(self.current_task.data)

    def _do_task(self, task: RWTask) -> object:
        loop = QEventLoop()
        self.timer_timeout.timeout.connect(loop.quit)
        self.sig_request.connect(loop.quit)

        self.current_task = task

        self.sig_timeout_start.emit(self.current_task.timeout)
        loop.exec_()

        self.sig_request.disconnect(loop.quit)
        self.timer_timeout.stop()
        self.timer_timeout.timeout.disconnect(loop.quit)

        self.busy = False

        if self.timeout_occurred:
            self.timeout_occurred = False
            print(f'Timeout occurred in task with command: {self.current_task.data}')
            self.current_task = None
            return None
        else:
            self.current_task = None
            return self.received_data

    def read_byte(self, addr):
        command = make_read_byte_command(addr).encode('ascii')
        return self._do_task(RWTask('K', addr, command, timeout=1000))

    def read_word(self, addr):
        command = make_read_word_command(addr).encode('ascii')
        return self._do_task(RWTask('L', addr, command, timeout=1000))

    @pyqtSlot()
    def on_timeout(self):
        """Обработчик таймаута"""
        self.timeout_occurred = True


class RsWorker(QObject):
    signal_pc_alt = pyqtSignal(tuple)
    sig_send_consts = pyqtSignal(dict)
    sig_rw_reply = pyqtSignal(int, str)
    sig_show_fbuffs = pyqtSignal(list)
    sig_progress_read_buffs = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.handler = RWHandler()

        self.timer_poll = QTimer()
        self.timer_poll.setInterval(1300)
        self.timer_poll.timeout.connect(self.on_timer_poll)
        self.handler.sig_timers_start.connect(self.timer_poll.start)
        self.is_polling = False

        self.raw_buffs = []

        self.pn = None
        self.sn = None

        self.flag_activity_rs_communication = False

    @pyqtSlot()
    def start(self):
        # Подписываемся на получение Commanded Position
        #self.handler.sig_normal_resp.connect(self.commanded_pos_print)

        # Устанавливаем normal op значением c 0 в BITE
        self.set_ofv_bite(0)
        self.handler.start()

    def set_ofv_bite(self, state: int):
        match state:
            case 0:
                self.handler.set_normal_task(RWTask('S', data=b'S01000000000032F9'))
            case 1:
                command: str = f'S01FFFFFFFF0032{_calculate_checksum('S01FFFFFFFF0032')}'
                self.handler.set_normal_task(RWTask('S', data=command.encode('ascii')))
            case 2:
                self.handler.set_normal_task(None)


    @pyqtSlot(tuple)
    def commanded_pos_print(self, br_zc):
        br, zc = br_zc
        print(f'BR: {br}, ZC: {zc}')

    def read_pc_alt(self):
        pc = self.handler.read_word(0xA004)
        if pc is None:
            return
        pc = (int(pc, 16) / 1024) * PSI_HPA
        alt = self.handler.read_word(0xA01E)
        alt = (int(alt, 16) / 4) * PSI_HPA
        self.signal_pc_alt.emit((pc, alt))

    def read_pn(self):
        pn = ''
        for i in range(0, 8):
            dat = self.handler.read_byte(0xA065 + i)
            if dat is None: return
            dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            pn += dat

        for i in range(0, 2):
            dat = self.handler.read_byte(0x1000 + i)
            if dat is None: return
            dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            pn += dat

        print(f'PN: {pn}')
        return pn

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
        consts = {
            'pc_offset_nvm' : (int(self.handler.read_word(0xA100), 16) / 2048) * PSI_HPA,
            'pc_offset_nvm_checksum' : (int(self.handler.read_word(0xA102), 16) / 2048) * PSI_HPA,
            'pc_check_offst' : (int(self.handler.read_word(0xA104), 16) / 2048) * PSI_HPA,
            'drift_comp_cnt' : int((self.handler.read_word(0xA106) + self.handler.read_word(0xA108)), 16),
            'pc_offset_fail_cnt' : int(self.handler.read_byte(0xA10A), 16),
            'pn': self.read_pn(),
            'sn': self.read_sn(),
        }

        self.pn = consts['pn']
        self.sn = consts['sn']

        self.sig_send_consts.emit(consts)


    @pyqtSlot(bool, int)
    def slot_read(self, state, addr):
        if state:
            reply = self.handler.read_byte(addr)
        else:
            reply = self.handler.read_word(addr)
        self.sig_rw_reply.emit(0, reply)

    @pyqtSlot(bool, int, int)
    def slot_write(self, state, addr, data):
        pass

    @pyqtSlot(QAbstractButton)
    def slot_bite_change(self, button: QAbstractButton):
        state = int(button.objectName()[-1:])
        self.set_ofv_bite(state)

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



