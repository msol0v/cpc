from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot, QIODevice, QEventLoop, Qt
import json
from queue import PriorityQueue

from PyQt5.QtSerialPort import QSerialPort


#################################  Utils  #######################################################
class FaultsBuffer():
    """48-байтовая запись буфера ошибок."""

    SIZE = 48

    def __init__(self, raw_buffer: list[str]):
        if len(raw_buffer) != self.SIZE:
            raise ValueError(
                f'Fault buffer must contain {self.SIZE} bytes, got {len(raw_buffer)}'
            )

        try:
            raw = bytes(int(value, 16) for value in raw_buffer)
        except (TypeError, ValueError) as exc:
            raise ValueError('Fault buffer contains an invalid hexadecimal byte') from exc

        def u16(offset: int) -> int:
            return int.from_bytes(raw[offset:offset + 2], byteorder='little', signed=False)

        def s16(offset: int) -> int:
            return int.from_bytes(raw[offset:offset + 2], byteorder='little', signed=True)

        self.fault_code = raw[0]
        self.intermittent_count = raw[1] & 0x07
        self.bbj_sel_in = bool(raw[1] & 0x08)
        self.flight_leg_counter = int.from_bytes(raw[2:6], byteorder='little', signed=False)
        self.elapsed_time_ticks = int.from_bytes(raw[6:10], byteorder='little', signed=False)
        self.elapsed_time_seconds = self.elapsed_time_ticks / 20
        self.disc_info1 = int.from_bytes(raw[10:13], byteorder='little', signed=False)
        self.disc_info2 = int.from_bytes(raw[13:16], byteorder='little', signed=False)

        # Форматы binary .5/.13/.7 дают 10/2/8 дробных бит; давление переводится в гПа.
        self.ambient_pressure_hpa = round((u16(16) / 1024) * PSI_HPA, 2)
        self.cabin_pressure_hpa = round((u16(18) / 1024) * PSI_HPA, 2)
        self.ambient_pressure_rate_slfpm = s16(20) / 4
        self.cabin_pressure_rate_slfpm = s16(22) / 4
        self.cruise_flight_level = s16(24)
        self.landing_field_elevation_ft = s16(26)
        self.ofv_position_deg = s16(28) / 256

        self.dcpcs_fault_word = u16(30)
        self.ext_sys_fault_word = u16(32)
        self.ctr_fault_word1 = u16(34)
        self.ctr_fault_word2 = u16(36)
        self.ofv_fault_word1 = u16(38)
        self.ofv_fault_word2 = u16(40)
        self.pnl_fault_word1 = u16(42)
        self.fault_matrix = int.from_bytes(raw[30:44], byteorder='little', signed=False)

        self.pref_hpa = round((u16(44) / 1024) * PSI_HPA, 2)
        self.ofv_command_br_deg = s16(46) / 256

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
    except (UnicodeDecodeError, ValueError):
        return False

PSI_HPA = 68.9475729318 # 1 psi = 68.9475729318 hPa

MESSAGE_LENGTH = {
            ord('P'): 11,
            ord('T'): 5,
            ord('U'): 7,
            ord('V'): 5,
            ord('W'): 7,
            ord('Z'): 1,
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

    # The conversion from encoded sensed position into degrees is: "convert hexadecimal number into decimal number and divide the decimal
    # number by 256 decimal"
    position = (position & 0xFFFF) * 256
    sended_position = f'{position & 0xFF:02X}{(position >> 8) & 0xFF:02X}'
    packet_raw = f'{id}{state}{bite}{sended_position}'
    full_packet = f'{packet_raw}{_calculate_checksum(packet_raw)}'
    return full_packet.encode('ascii')

############################################################################################################

class RWTask():
    _counter = 0  # Счётчик для сохранения порядка задач с одинаковым приоритетом
    
    def __init__(self, type: str, addr: int = 0, data: bytes = 0, timeout: int = 10, name: str = '', priority: int = 50):
        self.type = type
        self.addr = addr
        self.data = data
        self.timeout = timeout
        self.name = name
        self.result = None
        self.loop = None
        self.priority = priority  # Нижнее число = выше приоритет
        RWTask._counter += 1
        self.order = RWTask._counter  # Для сохранения порядка FIFO при одинаковом приоритете

class RWHandler(QObject):
    sig_timers_start = pyqtSignal()
    sig_port_opened = pyqtSignal(str)
    sig_port_closed = pyqtSignal()
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

        # Используем PriorityQueue вместо Queue
        self.task_queue = PriorityQueue()
        self.current_task = None
        self.busy = False
        self.timeout_occurred = False

        #For normal message
        self.normal_task: RWTask = None

        #Timers
        self.timer_normal_message = QTimer(self)
        self.timer_normal_message.setTimerType(Qt.PreciseTimer)
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
            self.sig_response_received.emit(bytes(packet))
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
        self.sig_port_opened.emit(self.port.portName())
        return True

    def set_normal_task(self, task: RWTask):
        self.normal_task = task

    @pyqtSlot()
    def slot_normal_op(self):
        if self.normal_task is None:
            return
        self.port.write(self.normal_task.data)

        now = datetime.now()
        current_time = now.strftime("%H:%M:%S.%f")
        print(f'{current_time}: [{self.normal_task.data}]')

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

        # Извлекаем задачу с наивысшим приоритетом (lowest priority number)
        priority, order, task = self.task_queue.get()
        self.current_task = task
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
        self.task_queue.put((task.priority, task.order, task))
        self._process_next_task()
        task.loop.exec_()
        return task.result

    def read_byte(self, addr, priority: int = 50):
        command = make_read_byte_command(addr).encode('ascii')
        return self._do_task(RWTask('K', addr, command, timeout=1000, priority=priority))

    def read_word(self, addr, priority: int = 50):
        command = make_read_word_command(addr).encode('ascii')
        return self._do_task(RWTask('L', addr, command, timeout=1000, priority=priority))

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
    PARAMETER_TABLE_POINTER_ADDRESS = 0x2084
    #---
    NVM_SOFTWARE_ISSUE_NUMBER_OFFSET = 0x0000
    NVM_SOFTWARE_LINK_NUMBER_OFFSET = 0x0002
    NVM_BIT_FAULT_MATRIX_LATCH_OFFSET = 0x0006
    NVM_FAULT_BUFFER_POINTER_OFFSET = 0x000A
    NVM_ELAPSED_TIME_COUNTER_OFFSET = 0x000C
    NVM_FAULT_BUFFER_CLEAR_FLAG_OFFSET = 0x001C
    NVM_SOFTWARE_CRC_CHECKSUM_OFFSET = 0x0082
    NVM_POWER_DOWN_BUFFER_OFFSET = 0x008A
    #---
    FAULT_MEMORY_START = 0x1000
    FAULT_MEMORY_END = 0x1FFE
    FAULT_BUFFER_COUNT = 42
    FAULT_BUFFER_SIZE = FaultsBuffer.SIZE
    FAULT_BUFFER_DATA_END = FAULT_MEMORY_START + FAULT_BUFFER_COUNT * FAULT_BUFFER_SIZE * 2 - 2
    FAULT_BYTE_READ_ATTEMPTS = 3
    BITE_MATRIX_SIZE = 14

    sig_send_consts = pyqtSignal(dict)
    sig_rw_reply = pyqtSignal(int, str)
    sig_bite_matrix = pyqtSignal(object)
    sig_bite_unavailable = pyqtSignal(str)
    sig_show_fbuffs = pyqtSignal(list)
    sig_progress_read_buffs = pyqtSignal(int)
    sig_error = pyqtSignal(str)
    sig_port_failed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()

        self.handler = RWHandler()
        self.handler.setParent(self)

        self.timer_bite = QTimer(self)
        self.timer_bite.setInterval(1000)
        self.timer_bite.timeout.connect(self.poll_bite_matrix)
        self.handler.sig_timers_start.connect(self.timer_bite.start)
        self._bite_polling = False

        self.raw_buffs = []

        self.consts = None

        self.flag_activity_rs_communication = False

        # Fault-buffers async read state
        self._fb_in_progress = False
        self._fb_total = self.FAULT_BUFFER_COUNT
        self._fb_current_n = 0
        self._fb_current_byte_index = 0
        self._fb_current_address = None
        self._fb_current_raw = []
        self._fb_fbuffs_accumulated = []
        self._fb_progress = 0

    @pyqtSlot()
    def start(self):
        self.handler.start()

    @pyqtSlot(str)
    def slot_connect_port(self, port_name):
        if self._bite_polling:
            self.timer_bite.stop()
            QTimer.singleShot(50, lambda: self.slot_connect_port(port_name))
            return
        if (self._fb_in_progress or self.handler.current_task is not None
                or not self.handler.task_queue.empty()):
            self.sig_port_failed.emit(port_name, 'RS-422 is busy; wait for the current operation to finish.')
            return

        port = self.handler.port
        previous_name = port.portName()
        was_open = port.isOpen()
        if port_name == previous_name and was_open:
            self.handler.sig_port_opened.emit(port_name)
            return

        self.timer_bite.stop()
        self.handler.timer_normal_message.stop()
        if was_open:
            port.close()
            self.handler.sig_port_closed.emit()
        self.handler.buffer.clear()
        port.setPortName(port_name)
        if self.handler.open():
            self.handler.sig_timers_start.emit()
            return

        reason = port.errorString()
        port.setPortName(previous_name)
        if was_open and self.handler.open():
            self.handler.sig_timers_start.emit()
        self.sig_port_failed.emit(port_name, reason)

    def read_pn_hw(self):
        hw = '0000-'
        addr = 0xA065
        for i in range(0, 8):
            dat = self.handler.read_byte(addr + i, priority=30)
            if dat is None: return
            try:
                dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            except UnicodeDecodeError:
                self.sig_error.emit(f'Не удалось декодировать в ASCII\n\r'
                                    f'read_pn_hw, addr: {addr + i:04X}, data: {dat}')
                dat = '?'
            if dat == '\r' or dat == '\n':
                dat = '?'
            hw += dat
        return hw

    def read_pn_sw(self):
        sw = ''
        addr = 0x1000
        for i in range(0, 2):
            dat = self.handler.read_byte(addr + i, priority=30)
            if dat is None: return
            try:
                dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            except UnicodeDecodeError:
                self.sig_error.emit(f'Не удалось декодировать в ASCII\n\r'
                                    f'read_pn_hw, addr: {addr + i:04X}, data: {dat}')
                dat = '0'
            sw += dat
        return sw

    def read_sw_ver(self):
        sw_ver = ''
        addr = 0x1010
        for i in range(0, 2):
            dat = self.handler.read_byte(addr + i, priority=30)
            if dat is None: return
            try:
                dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            except UnicodeDecodeError:
                self.sig_error.emit(f'Не удалось декодировать в ASCII\n\r'
                                    f'read_pn_hw, addr: {addr + i:04X}, data: {dat}')
                dat = '?'
            sw_ver += dat
        return sw_ver

    def read_sn(self):
        sn = ''
        addr = 0xA070
        for i in range(0, 7):
            dat = self.handler.read_byte(0xA070 + i, priority=30)
            if dat is None: return
            try:
                dat = int(dat, 16).to_bytes(1, byteorder='big').decode('ascii')
            except UnicodeDecodeError:
                self.sig_error.emit(f'Не удалось декодировать в ASCII\n\r'
                                    f'read_pn_hw, addr: {addr + i:04X}, data: {dat}')
                dat = '?'

            sn += dat
        print(f'SN: {sn}')
        return sn

    def find_parameter_address(self, offset: int, priority: int = 30) -> int:
        """Resolve a parameter address through the table rooted at 0x2084."""
        if not 0 <= offset <= 0xFFFF:
            raise ValueError(f'Invalid parameter-table offset: {offset}')

        table_base_reply = self.handler.read_word(
            self.PARAMETER_TABLE_POINTER_ADDRESS,
            priority=priority,
        )
        if table_base_reply is None:
            raise RuntimeError('Failed to read parameter-table base address at 2084H')

        table_base = int(table_base_reply, 16)
        pointer_entry_address = table_base + offset
        if pointer_entry_address > 0xFFFF:
            raise ValueError(
                f'Parameter-table entry is outside address space: {pointer_entry_address:05X}H'
            )

        parameter_address_reply = self.handler.read_word(
            pointer_entry_address,
            priority=priority,
        )
        if parameter_address_reply is None:
            raise RuntimeError(
                f'Failed to resolve parameter address at {pointer_entry_address:04X}H'
            )

        return int(parameter_address_reply, 16)

    @pyqtSlot()
    def poll_bite_matrix(self):
        if self._fb_in_progress or self._bite_polling:
            return
        self._bite_polling = True
        try:
            parameter_address = self.find_parameter_address(
                self.NVM_BIT_FAULT_MATRIX_LATCH_OFFSET, priority=40
            )
            address = parameter_address
            if address + self.BITE_MATRIX_SIZE - 1 > 0xFFFF:
                raise ValueError(f'Адрес матрицы BITE вне памяти: {address:04X}H')

            data = []
            for offset in range(self.BITE_MATRIX_SIZE):
                if self._fb_in_progress:
                    return
                reply = self.handler.read_byte(address + offset, priority=40)
                if reply is None:
                    raise RuntimeError(f'Нет ответа для BITE по адресу {address + offset:04X}H')
                data.append(int(reply, 16))
            self.sig_bite_matrix.emit(int.from_bytes(bytes(data), byteorder='little'))
        except Exception as exc:
            self.sig_bite_unavailable.emit(str(exc))
        finally:
            self._bite_polling = False

    @classmethod
    def next_fault_memory_address(cls, address: int) -> int:
        """Следующий байт в кольце из 42 записей."""
        if not cls.FAULT_MEMORY_START <= address <= cls.FAULT_BUFFER_DATA_END:
            raise ValueError(f'Address {address:04X}H is outside fault memory')
        if address & 1:
            raise ValueError(f'Fault-memory address must be even: {address:04X}H')
        if address == cls.FAULT_BUFFER_DATA_END:
            return cls.FAULT_MEMORY_START
        return address + 2

    def read_fault_buffer(self, start_address: int, priority: int = 30) -> tuple[list[str], int]:
        """Read one 48-byte buffer and return it with the next circular address."""
        address = start_address
        buffer = []
        for _ in range(self.FAULT_BUFFER_SIZE):
            data_byte = self.handler.read_byte(address, priority=priority)
            if data_byte is None:
                raise RuntimeError(f'Failed to read fault buffer byte at {address:04X}H')
            buffer.append(data_byte)
            address = self.next_fault_memory_address(address)
        return buffer, address

    @pyqtSlot()
    def slot_get_consts(self):
        self.sig_error.emit('Адреса констант не подтверждены в СММ')


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
    def test(self):
        pass

    def _stop_fault_buffer_read(self):
        self._fb_in_progress = False

    def _fb_step(self):
        # internal step for asynchronous reading of fault buffers
        if not self._fb_in_progress:
            return

        # If all buffers read -> finish
        if self._fb_current_n >= self._fb_total:
            self._stop_fault_buffer_read()
            self.sig_show_fbuffs.emit(self._fb_fbuffs_accumulated)
            # ensure progress completion
            self.sig_progress_read_buffs.emit(100)
            print(f'Finished reading {len(self._fb_fbuffs_accumulated)} fault buffers')
            return

        addr = self._fb_current_address

        try:
            dat = None
            for attempt in range(1, self.FAULT_BYTE_READ_ATTEMPTS + 1):
                dat = self.handler.read_byte(addr, priority=30)
                if dat is not None:
                    break
                print(f'Повтор чтения NVM {addr:04X}H: попытка {attempt}')
        except Exception as e:
            self._stop_fault_buffer_read()
            self.sig_error.emit(f'Error while reading fault buffers at addr {addr:04X}: {e}')
            return

        # if device timed out or returned None -> abort
        if dat is None:
            self._stop_fault_buffer_read()
            self.sig_error.emit(
                f'Failed to read fault buffer byte at addr {addr:04X} '
                f'after {self.FAULT_BYTE_READ_ATTEMPTS} attempts'
            )
            return

        self._fb_current_raw.append(dat)
        self._fb_current_address = self.next_fault_memory_address(addr)

        self._fb_current_byte_index += 1

        # One new-format fault buffer contains 48 bytes.
        if self._fb_current_byte_index >= self.FAULT_BUFFER_SIZE:
            try:
                fb = FaultsBuffer(self._fb_current_raw)
            except Exception as e:
                self._stop_fault_buffer_read()
                self.sig_error.emit(f'Error parsing fault buffer #{self._fb_current_n}: {e}')
                return

            print(f'Fault buffer #{self._fb_current_n}: code {fb.fault_code}')
            self._fb_fbuffs_accumulated.append(fb)
            self.raw_buffs.extend(self._fb_current_raw)

            self._fb_progress = round(
                (self._fb_current_n + 1) * 100 / self._fb_total
            )
            self.sig_progress_read_buffs.emit(self._fb_progress)

            # prepare for next buffer
            self._fb_current_n += 1
            self._fb_current_byte_index = 0
            self._fb_current_raw = []

        # schedule next step to give Qt loop a chance to process other events
        QTimer.singleShot(0, self._fb_step)

    @pyqtSlot()
    def read_fbuffs(self):
        # Start asynchronous read of fault buffers. If already running, ignore.
        if self._fb_in_progress:
            return
        
        # initialize state
        self._fb_in_progress = True
        self.sig_bite_unavailable.emit('Чтение буферов NVM')
        self._fb_current_n = 0
        self._fb_current_byte_index = 0
        self._fb_current_address = self.FAULT_MEMORY_START
        self._fb_current_raw = []
        self._fb_fbuffs_accumulated = []
        self._fb_progress = 0
        self.raw_buffs = []

        self.sig_progress_read_buffs.emit(0)

        # kick off the async stepping
        QTimer.singleShot(0, self._fb_step)
