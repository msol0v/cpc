import time
from typing import Optional, Dict, List, Any, Callable
from functools import lru_cache, wraps
import lables_cache

from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    QTimer,
    QThread,
    pyqtSlot,
    QIODevice,
    QByteArray
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

class LabelsCache():
    def __init__(self):
        self.label_handlers: Dict[str, int] = {}


class ArincWorker(QObject):
    """
    Воркер для работы с ARINC в отдельном потоке.
    Читает порт, парсит слова и отправляет сигналы в главный поток.
    """

    # Сигналы для передачи данных в главный поток
    sig_error = pyqtSignal(str)
    sig_connected = pyqtSignal()
    sig_bus_activity = pyqtSignal(bool)

    # Сигналы для каждого типа меток
    sig_352 = pyqtSignal(dict)
    sig_353 = pyqtSignal(dict)
    sig_163 = pyqtSignal(int)
    sig_057 = pyqtSignal(dict)

    # Сигналы для слов BITE
    sig_104 = pyqtSignal(int)
    sig_105 = pyqtSignal(int)
    sig_106 = pyqtSignal(int)
    sig_107 = pyqtSignal(int)
    sig_110 = pyqtSignal(int)
    sig_111 = pyqtSignal(int)

    # Общий сигнал для неизвестных меток (опционально)
    sig_unknown_label = pyqtSignal(int, int)  # label_int, word_int

    def __init__(self, port_name: str):
        super().__init__()

        # Параметры порта
        self._port_name = port_name
        self._baud_rate = 115200
        self.port = None

        # Состояние
        self._connected = False
        self._waiting_for_version = True
        self._flag_sdac_activity = False

        # Буфер для накопления данных
        self._rx_buffer = b''

        # Регистр обработчиков (нужен только для маппинга, но сами обработчики не вызываются)
        self.registry = HandlerRegistry()
        self._register_handlers()  # Регистрируем метки для маппинга
        self.handlers = self.registry.label_handlers
        self.rx_labels_int = self.registry.rx_labels_int
        del self.registry #Освобождаем память. Регистрация уже прошла

        # Таймеры для периодической отправки (работают в этом же потоке)
        self._setup_timers()

        # Счетчик активности шины
        self._last_activity_time = time.time()

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
            self.sig_error.emit(f"Cannot open port: {self._port_name}")
            return False

        print(f"Port {self._port_name} opened successfully")

        # Отправляем команду version
        self._waiting_for_version = True
        self.port.write('version\n'.encode('utf-8'))

        # Запускаем таймер активности
        self.activity_timer.start()

        return True

    @pyqtSlot()
    def stop(self):
        """Остановка работы"""
        self.activity_timer.stop()
        self.timer_5min.stop()
        self.timer_1sec.stop()
        self.timer_100msec.stop()
        self.timer_65msec.stop()
        self.timer_120msec.stop()
        self.timer_900msec.stop()

        if self.port and self.port.isOpen():
            self.port.close()
            self._connected = False

    @pyqtSlot(QSerialPort.SerialPortError)
    def handle_error(self, error):
        """Обработка ошибок порта"""
        if error != QSerialPort.NoError:  # Игнорируем "нет ошибки"
            error_string = self.port.errorString() if self.port else "Unknown error"
            print(f"Port error: {error} - {error_string}")
            self.sig_error.emit(f"Port error: {error_string}")

    def _setup_timers(self):
        """Настройка таймеров"""

        # Таймеры отправки слов
        self.timer_1sec = QTimer()
        self.timer_100msec = QTimer()
        self.timer_65msec = QTimer()
        self.timer_120msec = QTimer()
        self.timer_900msec = QTimer()

        self.timer_1sec.setInterval(1000)
        self.timer_100msec.setInterval(100)
        self.timer_65msec.setInterval(65)
        self.timer_120msec.setInterval(120)
        self.timer_900msec.setInterval(900)

        self.timer_1sec.timeout.connect(self.slot_timer_1sec)
        self.timer_100msec.timeout.connect(self.slot_timer_100msec)
        self.timer_65msec.timeout.connect(self.slot_timer_65msec)
        self.timer_120msec.timeout.connect(self.slot_timer_120msec)
        self.timer_900msec.timeout.connect(self.slot_timer_900msec)

        # Таймер проверки активности шины
        self.activity_timer = QTimer()
        self.activity_timer.setInterval(500)  # Проверка каждые 500 мс
        self.activity_timer.timeout.connect(self._check_activity)

        self.sig_connected.connect(self.timer_1sec.start)
        self.sig_connected.connect(self.timer_100msec.start)
        self.sig_connected.connect(self.timer_65msec.start)
        self.sig_connected.connect(self.timer_120msec.start)
        self.sig_connected.connect(self.timer_900msec.start)
        self.sig_connected.connect(self.activity_timer.start)

    def _check_activity(self):
        """Проверка активности шины"""
        if time.time() - self._last_activity_time > 1.0:
            # Нет активности более 1 секунды
            if self._flag_sdac_activity:
                self._flag_sdac_activity = False
                self.sig_bus_activity.emit(False)

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
            if line_str == 'ver.USB-BSCk0':
                self._connected = True
                self._waiting_for_version = False
                self.sig_connected.emit()
                self._configure_fizz()  # Настраиваем преобразователь
                QThread.msleep(300) #Ожидание, пока порты включатся
                print("Fizz connected successfully")
            return

        # Обработка ARINC слов
        if line.startswith(b'dat'):
            try:
                # datNxxxxYYYY\n
                word_b: bytes = line[4 : -5]
                label_b = word_b[-1:]
                # Конвертируем hex в int
                word_int = int.from_bytes(word_b, 'big')
                label_int = int.from_bytes(label_b, 'big')

                # Обновляем активность
                self._flag_sdac_activity = True

                # Вызываем нужный сигнал в зависимости от метки
                self.call_word_handler(label_int, word_int)

            except ValueError as e:
                print(f"Error converting hex: {e}")
            except Exception as e:
                print(f"Error parsing ARINC word: {e}")

    def call_word_handler(self, label_int: int, word_int: int):
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
        #QThread.msleep(50)
        #self.port.clear()

    @pyqtSlot(dict)
    def slot_change_uut_word(self, words: dict):
        for label, word in words.items():
            self.uut_in_words[label] = word

        print(self.uut_in_words)

    @pyqtSlot()
    def slot_timer_1sec(self):
        self.sig_bus_activity.emit(self._flag_sdac_activity)
        self._flag_sdac_activity = False  # Сбрасываем флаг
        words = [
            self.uut_in_words.get('125'),
            self.uut_in_words.get('126'),
            self.uut_in_words.get('260'),
            self.uut_in_words.get('301'),
            self.uut_in_words.get('302'),
            self.uut_in_words.get('303'),
        ]
        self.send_word_list(words)
        # self.send_word_list(['855254AA', 'E000006A', '14CA140D',
        #                       '529F3883', 'C99B1043', '00010CC3'])

    @pyqtSlot()
    def slot_timer_100msec(self):
        words = [self.uut_in_words.get('246')]
        self.send_word_list(words)
        #self.send_word_list(['E7F80165'])
        pass

    @pyqtSlot()
    def slot_timer_65msec(self):
        words = [self.uut_in_words.get('210')]
        self.send_word_list(words)
        #self.send_word_list(['6C800111'])
        pass

    @pyqtSlot()
    def slot_timer_120msec(self):
        words = [self.uut_in_words.get('227')]
        self.send_word_list(words)
        #self.send_word_list(['1105C0E9'])
        pass

    @pyqtSlot()
    def slot_timer_900msec(self):
        words = [
            self.uut_in_words.get('351'),
            self.uut_in_words.get('256')
        ]
        self.send_word_list(words)
        #self.send_word_list(['00002097', '60FA0175'])
        pass

    # Методы для отправки данных
    def send_word_list(self, word_list: list):
        """Отправка списка слов ARINC"""
        if not self._connected:
            return
        for word in word_list:
            fizz_command = f'send 1 {word}'
            self.port.write((fizz_command + '\n').encode('utf-8'))

    @pyqtSlot(bool)
    def slot_fizz_speed(self, is_high: bool):
        """Изменение скорости передачи"""
        if not self._connected:
            return
        cmd = 'transmitter_freq 1\n' if is_high else 'transmitter_freq 3\n'
        self.port.write(cmd.encode('utf-8'))

    def _register_handlers(self):
        """Регистрация меток (нужно только для маппинга)"""

        @self.registry.label_handler('57')
        def label_57(self, word: int):
            @lru_cache(maxsize=256)
            def _compute_dict(w: int) -> Dict[str, int]:
                return {
                    'sdi': (word >> 8) & 0x03,
                    'sys_in_control': (word >> 10) & 0x01,
                    'sys_status': (word >> 11) & 0x01,
                    'lfe_from_fms': (word >> 12) & 0x01,
                    'excessive_cabin_altitude': (word >> 13) & 0x01,
                    'low_differential_pressure': (word >> 14) & 0x01,
                    'preplanned_descent_info': (word >> 15) & 0x01,
                    'lfes_status': (word >> 16) & 0x01,
                    'used_adirs_channel': (word >> 17) & 0x03,
                    'fms_enable': (word >> 19) & 0x01,
                    'flight_modes': (word >> 20) & 0x07,
                    'fms_selection': (word >> 23) & 0x03,
                    'fms_use': (word >> 25) & 0x01,
                    'qnh_from_fms': (word >> 26) & 0x01,
                    'class_2_fault': (word >> 27) & 0x01,
                    'ssm': (word >> 29) & 0x03,
                }
            self.sig_057.emit(_compute_dict(word))

        @self.registry.label_handler('352')
        def label_352(self, word: int):
            @lru_cache(maxsize=256)
            def _compute_dict(w: int) -> Dict[str, int]:
                return {
                    'SDI': (word >> 8) & 0x03,
                    'FAULT_WARN_WR': (word >> 10) & 0x01,
                    'SYS_IN_CNTL_IN': (word >> 12) & 0x01,
                    'DO_SPARE_1_WR': (word >> 13) & 0x01,
                    'DO_SPARE_2_WR': (word >> 14) & 0x01,
                    'DO_SPARE_3_WR': (word >> 15) & 0x01,
                    'PASS_SIGN_WR': (word >> 16) & 0x01,
                    'ENG_1_N2': (word >> 18) & 0x01,
                    'DI_SPARE_3': (word >> 19) & 0x01,
                    'ENG_2_N2': (word >> 20) & 0x01,
                    'DI_SPARE_4': (word >> 21) & 0x01,
                    'LDG_GEAR_NORM': (word >> 22) & 0x01,
                    'DI_SPARE_5': (word >> 23) & 0x01,
                    'LDG_GEAR_ESS': (word >> 24) & 0x01,
                    'DI_SPARE_6': (word >> 25) & 0x01,
                    'SSM': (word >> 29) & 0x03,
                }
            self.sig_352.emit(_compute_dict(word))

        @self.registry.label_handler('353')
        def label_353(self, word: int):
            @lru_cache(maxsize=256)
            def _compute_dict(w: int) -> Dict[str, int]:
                return {
                    'SDI': (word >> 8) & 0x03,
                    'MANUAL_MODE': (word >> 10) & 0x01,
                    'SYS_ID': (word >> 11) & 0x01,
                    'DITCH_SWITCH': (word >> 12) & 0x01,
                    'EMER_RAM_AIR': (word >> 13) & 0x01,
                    'RS_SELECT': (word >> 14) & 0x01,
                    'HI_CRFL': (word >> 15) & 0x01,
                    'FMS_ENABLE': (word >> 16) & 0x01,
                    'DI_SPARE_2': (word >> 17) & 0x01,
                    'SSM': (word >> 29) & 0x03,
                }
            self.sig_353.emit(_compute_dict(word))

        @self.registry.label_handler('163')
        def label_163(self, word: int):
            data = (word >> 13) & 0xFFF
            self.sig_163.emit(data)

        @self.registry.label_handler('104')
        def label_104(self, word: int):
            data = (word >> 10) & 0x7FFFF
            self.sig_104.emit(data)

        @self.registry.label_handler('105')
        def label_105(self, word: int):
            data = (word >> 10) & 0x7FFFF
            self.sig_105.emit(data)

        @self.registry.label_handler('106')
        def label_106(self, word: int):
            data = (word >> 10) & 0x7FFFF
            self.sig_106.emit(data)

        @self.registry.label_handler('107')
        def label_107(self, word: int):
            data = (word >> 10) & 0x7FFFF
            self.sig_107.emit(data)

        @self.registry.label_handler('110')
        def label_110(self, word: int):
            data = (word >> 10) & 0x7FFFF
            self.sig_110.emit(data)

        @self.registry.label_handler('111')
        def label_111(self, word: int):
            data = (word >> 10) & 0x7FFFF
            self.sig_111.emit(data)

        @self.registry.label_handler('356')
        def label_356(self, word: int):
            #print(f'UUT resp {word:#010X}')
            pass

        @self.registry.label_handler('365')
        def label_365(self, word: int):
            print('EOT from UUT')
            pass

        @self.registry.label_handler('144')
        def label_144(self, word: int):
            pass

        @self.registry.label_handler('150')
        def label_150(self, word: int):
            pass

        @self.registry.label_handler('151')
        def label_151(self, word: int):
            pass

        @self.registry.label_handler('153')
        def label_153(self, word: int):
            pass

        @self.registry.label_handler('277')
        def label_277(self, word: int):
            pass

        @self.registry.label_handler('377')
        def label_377(self, word: int):
            pass

        @self.registry.label_handler('301')
        def label_301(self, word: int):
            pass


