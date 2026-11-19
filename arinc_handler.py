import time
from typing import Dict, Callable
import lables_cache
import json

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    QTimer,
    pyqtSlot,
    QIODevice,
)
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo




def reverse_number(n: int) -> int:
    '''Переворачивает число побитово'''
    reversed_value = 0
    for i in range(8):
        if n & (1 << i):
            reversed_value |= (1 << (7 - i))
    return reversed_value

def base8_to_int(label_octet: str) -> int:
    """
    Преобразует строку лейбла восьмиричной сс в int

    Args:
        label_octet: строка с восьмеричным числом (например, '352')

    Returns:
        int: значение метки (инвертированное)
    """
    decimal_value = int(label_octet, 8)
    return reverse_number(decimal_value)

def int_to_base8(label: int) -> str:
    r = reverse_number(label)
    return oct(r)

class HandlerRegistry:
    """
    Регистратор обработчиков слов Arinc

    Example:
        registry = HandlerRegistry()

        @registry.label_handler('352')
        def label_352(self, word):
            # обработка метки 352
            pass
    """

    def __init__(self):
        self.label_handlers: Dict[int, Callable] = {}  # Обработчики по меткам (ключ - int)
        self.rx_labels_int: Dict[int, str] = {}  # [int hex] = str base 8

    def label_handler(self, label: str):
        """
        Декоратор для регистрации обработчика метки

        Args:
            label: строка с восьмеричной меткой (например, '352')
        """

        def decorator(func):
            label_int = base8_to_int(label)
            self.label_handlers[label_int] = func
            self.rx_labels_int[label_int] = label
            return func

        return decorator



class ArincWorker(QObject):
    """
    Воркер для работы с ARINC в отдельном потоке.
    Читает порт, парсит слова и отправляет сигналы в главный поток.
    """

    # Сигналы для передачи данных в главный поток
    sig_error = pyqtSignal(str)
    sig_connected = pyqtSignal()
    sig_bus_activity = pyqtSignal(dict)
    sig_start_activity_timer = pyqtSignal()
    sig_timer_connecting_start = pyqtSignal()
    sig_timer_connecting_stop = pyqtSignal()

    # Общий сигнал для неизвестных меток (опционально)
    sig_unknown_label = pyqtSignal(int, int)  # label_int, word_int

    def __init__(self, port_name: str):
        super().__init__()

        with open('config.json', 'r', encoding='utf-8') as f:
            self.config = json.load(f)



        # Параметры порта
        self._port_name = self.config['ports']['arinc']
        self._baud_rate = 115200
        self.port = None

        # Состояние
        self._connected = False
        self._waiting_for_version = True
        self.sdac_activity = {'sdac_0':False, 'sdac_1':False}

        # Буфер для накопления данных
        self._rx_buffer = b''

        # Регистр обработчиков (нужен только для маппинга, но сами обработчики не вызываются)
        self.registry = HandlerRegistry()
        self._register_handlers()  # Регистрируем метки для маппинга
        self.handlers = self.registry.label_handlers
        self.rx_labels_int = self.registry.rx_labels_int
        del self.registry #Освобождаем память. Регистрация уже прошла

        # Таймеры контроля подключения и активности шины
        self._setup_timers()

        # Счетчик активности шины
        self._last_activity_time = time.time()

        if self.config.get('statistic'):
            # Создаем кэш для статистики
            self.labels_cache = lables_cache.LabelsCache(stats_interval=120)

        self.uut_in_words = {}

    @pyqtSlot()
    def slot_connect(self):
        """
        Слот для подключения к порту.
        Вызывается из главного потока через сигнал.
        """
        print(f"Connecting to {self._port_name}...")

        # Создаем и открываем порт
        self.port = QSerialPort()
        self.port.setPortName(self._port_name)
        self.port.setBaudRate(self._baud_rate)

        # Подключаем сигналы
        self.port.readyRead.connect(self.handle_ready_read)
        # Подключаем сигнал errorOccurred к слоту, который принимает параметр
        self.port.errorOccurred.connect(self.handle_error)

        # Открываем порт
        mode = QIODevice.OpenMode(QIODevice.ReadWrite)
        if not self.port.open(mode):
            self.stop()
            return False

        print(f"ARINC port {self._port_name} opened successfully")

        # Отправляем команду version
        self._waiting_for_version = True
        self.port.write('version\n'.encode('utf-8'))

        # Запускаем таймер активности
        self.sig_timer_connecting_start.emit()

        return True

    @pyqtSlot()
    def stop(self):
        """Остановка работы"""
        self.activity_timer.stop()
        self.timer_50ms.stop()
        self.timer_63ms.stop()
        self.timer_100ms.stop()
        self.timer_200ms.stop()

        if self.port and self.port.isOpen():
            self.port.close()
            self._connected = False

    @pyqtSlot(QSerialPort.SerialPortError)
    def handle_error(self, error):
        """Обработка ошибок порта"""
        if error != QSerialPort.NoError:  # Игнорируем "нет ошибки"
            error_string = f'Port {self._port_name} error\n\r{self.port.errorString()}' if self.port else "Unknown error"
            self.sig_error.emit(error_string)

    def _setup_timers(self):
        """Настройка таймеров"""

        # Периоды входных ARINC-слов по CMM 21-33-20, стр. 1005 и 1007.
        self.timer_50ms = QTimer(self)
        self.timer_63ms = QTimer(self)
        self.timer_100ms = QTimer(self)
        self.timer_200ms = QTimer(self)

        self.timer_50ms.setInterval(50)    # 20 Hz: PNL
        self.timer_63ms.setInterval(63)    # 15.87 Hz: DADC altitude, within 16 Hz +/-10%
        self.timer_100ms.setInterval(100)  # 10 Hz: DADC CAS
        self.timer_200ms.setInterval(200)  # 5 Hz: SMC

        self.timer_50ms.timeout.connect(self.slot_timer_50ms)
        self.timer_63ms.timeout.connect(self.slot_timer_63ms)
        self.timer_100ms.timeout.connect(self.slot_timer_100ms)
        self.timer_200ms.timeout.connect(self.slot_timer_200ms)

        # Таймер проверки активности шины
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(1000)
        self.activity_timer.setSingleShot(True)
        self.activity_timer.timeout.connect(self._handle_bus_timeout)

        self.timer_connecting = QTimer(self)
        self.timer_connecting.setInterval(1000)
        self.timer_connecting.setSingleShot(True)
        self.sig_timer_connecting_start.connect(self.timer_connecting.start)
        self.sig_timer_connecting_stop.connect(self.timer_connecting.stop)
        self.timer_connecting.timeout.connect(self.slot_connecting_timeout)

        self.sig_connected.connect(self.timer_50ms.start)
        self.sig_connected.connect(self.timer_63ms.start)
        self.sig_connected.connect(self.timer_100ms.start)
        self.sig_connected.connect(self.timer_200ms.start)
        self.sig_start_activity_timer.connect(self.activity_timer.start)

    @pyqtSlot()
    def _handle_bus_timeout(self):
        self.sdac_activity = {'sdac_0': False, 'sdac_1': False}
        self.sig_bus_activity.emit(self.sdac_activity)

        error_msg = 'Error: SDAC Bus activity timeout (no data > 1 sec)\n\r'
        self.sig_error.emit(error_msg)

    @pyqtSlot()
    def slot_connecting_timeout(self):
        self.stop()
        self.sig_error.emit('Timeout connecting to Fizika Pribor')


    @pyqtSlot()
    def handle_ready_read(self):
        """Обработка входящих данных (в потоке порта)"""
        # Читаем все доступные данные
        data = self.port.readAll()
        if data.isEmpty():
            return

        # Конвертируем в bytes и добавляем в буфер
        self._rx_buffer += bytes(data)

        # Обновляем время активности
        self._last_activity_time = time.time()

        # Обрабатываем все полные строки
        while True:
            line_end = self._rx_buffer.find(b'\n')
            if line_end == -1:
                break

            line = self._rx_buffer[:line_end + 1]
            self._rx_buffer = self._rx_buffer[line_end + 1:]

            # Обрабатываем строку
            self._process_line(line)

    def _process_line(self, line: bytes):
        """Обработка одной строки данных"""
        if not line:
            return

        # Обработка ответа на команду version
        if self._waiting_for_version:
            line_str = line.decode('utf-8', errors='ignore').strip()
            if line_str == 'ver.USB-BSCMk0':
                self.sig_timer_connecting_stop.emit()
                self._connected = True
                self._waiting_for_version = False
                self.sig_connected.emit()
                self._configure_fizz()  # Настраиваем преобразователь
                self.sig_start_activity_timer.emit()
            return

        # Обработка ARINC слов
        if line.startswith(b'dat'):
            self.sig_start_activity_timer.emit()
            try:
                # datNxxxxYYYY\n

                chan = int(line[3:4])
                word_b: bytes = line[4 : -5]
                label_b = word_b[-1:]
                # Конвертируем hex в int
                word_int = int.from_bytes(word_b, 'big')
                label_int = int.from_bytes(label_b, 'big')

                # Обновляем активность
                self.sdac_activity[f'sdac_{chan}'] = True
                self.sig_bus_activity.emit(self.sdac_activity)

                # Вызываем нужный сигнал в зависимости от метки
                self.call_word_handler(label_int, word_int)

            except ValueError as e:
                print(f"Error converting hex: {e}")
            except Exception as e:
                print(f"Error parsing ARINC word: {e}")

    def call_word_handler(self, label_int: int, word_int: int):
        if self.config.get('statistic'):
            #Кэш для статистики
            label_octal = int_to_base8(label_int)
            self.labels_cache.put(label_octal, word_int)

        _handler = self.handlers.get(label_int)
        if _handler is None:
            #print(f"No handler for label {oct(reverse_number(label_int))}")
            return

        _handler(self, word_int)

    def _configure_fizz(self):
        """Настройка преобразователя"""
        self.port.write('start 1\n'.encode('utf-8'))
        self.port.write('start 2\n'.encode('utf-8'))
        self.port.write('transmitter_freq 3\n'.encode('utf-8'))  # ARINC low speed

    @pyqtSlot(dict)
    def slot_change_uut_word(self, words: dict):
        self.uut_in_words.update(words)

    @pyqtSlot()
    def slot_timer_50ms(self):
        self.send_word_list([
            self.uut_in_words.get('107'),
            self.uut_in_words.get('127'),
            self.uut_in_words.get('271'),
        ])

    @pyqtSlot()
    def slot_timer_63ms(self):
        self.send_word_list([
            self.uut_in_words.get('203'),
            self.uut_in_words.get('204'),
            self.uut_in_words.get('220'),
        ])

    @pyqtSlot()
    def slot_timer_100ms(self):
        self.send_word_list([self.uut_in_words.get('206')])

    @pyqtSlot()
    def slot_timer_200ms(self):
        self.send_word_list([
            self.uut_in_words.get('344'),
            self.uut_in_words.get('346'),
        ])

    def send_word_list(self, word_list: list):
        """Отправить последние заданные ARINC-слова через первый канал."""
        if not self._connected:
            return
        for word in word_list:
            if word is None:
                continue
            self.port.write(f'send 1 {word}\n'.encode('utf-8'))

    @pyqtSlot(bool)
    def slot_fizz_speed(self, is_high: bool):
        """Изменение скорости передачи"""
        if not self._connected:
            return
        cmd = 'transmitter_freq 1\n' if is_high else 'transmitter_freq 3\n'
        self.port.write(cmd.encode('utf-8'))

    @staticmethod
    def _decode_bnr(word: int, lsb_bit: int, resolution: float) -> Dict[str, object]:
        """Декодировать BNR со знаком в ARINC bit 29."""
        magnitude_width = 29 - lsb_bit
        magnitude = (word >> (lsb_bit - 1)) & ((1 << magnitude_width) - 1)
        sign = (word >> 28) & 0x01
        value = (-magnitude if sign else magnitude) * resolution
        return {
            'sdi': (word >> 8) & 0x03,
            'value': value,
            'ssm': (word >> 29) & 0x03,
            'parity': (word >> 31) & 0x01,
        }

    @staticmethod
    def _decode_bnr_raw(word: int) -> Dict[str, int]:
        """Извлечь BNR-поля, если масштаб и LSB еще не подтверждены."""
        return {
            'sdi': (word >> 8) & 0x03,
            'data_bits_11_28': (word >> 10) & 0x3FFFF,
            'sign': (word >> 28) & 0x01,
            'ssm': (word >> 29) & 0x03,
            'parity': (word >> 31) & 0x01,
        }

    @staticmethod
    def _decode_discrete(word: int) -> Dict[str, object]:
        """Извлечь 19 дискретных битов ARINC 11-29."""
        return {
            'sdi': (word >> 8) & 0x03,
            'data_bits': {
                bit: (word >> (bit + 9)) & 0x01
                for bit in range(1, 20)
            },
            'ssm': (word >> 29) & 0x03,
            'parity': (word >> 31) & 0x01,
        }

    @staticmethod
    def _decode_fault_word(word: int, first_fault_code: int) -> Dict[str, object]:
        """Декодировать 16 флагов BIT Fault Matrix из ARINC bits 11-26."""
        fault_bits = (word >> 10) & 0xFFFF
        return {
            'sdi': (word >> 8) & 0x03,
            'fault_bits': fault_bits,
            'active_fault_codes': [
                first_fault_code + bit
                for bit in range(16)
                if fault_bits & (1 << bit)
            ],
            'ssm': (word >> 29) & 0x03,
            'parity': (word >> 31) & 0x01,
        }

    def _register_handlers(self):
        """Регистрация меток (нужно только для маппинга)"""

        # Выходные слова CPC 7121-19971-01AC.
        @self.registry.label_handler('057')
        def label_057(self, word: int):
            result = {
                'sdi': (word >> 8) & 0x03,
                'auto_in_control': (word >> 10) & 0x01,
                'auto_channel_fail': (word >> 11) & 0x01,
                'controller_is_master': (word >> 12) & 0x01,
                'max_dp_limiter_active': (word >> 13) & 0x01,
                'pressure_switch_active': (word >> 14) & 0x01,
                'flight_mode': (word >> 15) & 0x07,
                'dadc_1_used': (word >> 18) & 0x01,
                'smc_1_used': (word >> 19) & 0x01,
                'operation_mode': (word >> 20) & 0x03,
                'cas_range': (word >> 22) & 0x03,
                'n1_low_or_invalid': (word >> 24) & 0x01,
                'n2_low_or_invalid': (word >> 25) & 0x01,
                'b737x_selected': (word >> 26) & 0x01,
                'cpalt_source': (word >> 27) & 0x03,
                'ssm': (word >> 29) & 0x03,
                'parity': (word >> 31) & 0x01,
            }
            # Получили DISCR1: режимы и основной статус контроллера.

        @self.registry.label_handler('060')
        def label_060(self, word: int):
            result = self._decode_discrete(word)
            # Получили DISCR2: состояния дискретных входов и источников.

        @self.registry.label_handler('100')
        def label_100(self, word: int):
            result = self._decode_bnr_raw(word)
            # Получили BNR-параметр label 100; масштаб нужно взять из ARINC ICD.

        @self.registry.label_handler('107')
        def label_107(self, word: int):
            result = self._decode_bnr(word, lsb_bit=13, resolution=1.0)
            # Получили SCRFL: выбранную крейсерскую высоту, ft.

        @self.registry.label_handler('127')
        def label_127(self, word: int):
            result = self._decode_bnr(word, lsb_bit=13, resolution=1.0)
            # Получили SLFE: выбранную высоту аэродрома посадки, ft.

        @self.registry.label_handler('144')
        def label_144(self, word: int):
            result = self._decode_bnr_raw(word)
            # Получили BNR-параметр label 144; масштаб нужно взять из ARINC ICD.

        @self.registry.label_handler('150')
        def label_150(self, word: int):
            result = self._decode_bnr_raw(word)
            # Получили BNR-параметр label 150; масштаб нужно взять из ARINC ICD.

        @self.registry.label_handler('152')
        def label_152(self, word: int):
            result = self._decode_bnr_raw(word)
            # Получили BNR-параметр label 152; масштаб нужно взять из ARINC ICD.

        @self.registry.label_handler('270')
        def label_270(self, word: int):
            result = self._decode_discrete(word)
            # Получили CTR_DISC_STAT: дискретный статус контроллера для панели.

        @self.registry.label_handler('271')
        def label_271(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=96)
            # Получили PNL_FAULT_WORD: коды отказов 96-111.

        @self.registry.label_handler('350')
        def label_350(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=0)
            # Получили SYS_FAULT_WORD: коды отказов 0-15.

        @self.registry.label_handler('351')
        def label_351(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=16)
            # Получили SYS_EXT_FAULT_WORD: коды отказов 16-31.

        @self.registry.label_handler('352')
        def label_352(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=32)
            # Получили CTR_FAULT_WORD1: коды отказов 32-47.

        @self.registry.label_handler('353')
        def label_353(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=48)
            # Получили CTR_FAULT_WORD2: коды отказов 48-63.

        @self.registry.label_handler('354')
        def label_354(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=64)
            # Получили OFV_FAULT_WORD1: коды отказов 64-79.

        @self.registry.label_handler('355')
        def label_355(self, word: int):
            result = self._decode_fault_word(word, first_fault_code=80)
            # Получили OFV_FAULT_WORD2: коды отказов 80-95.


