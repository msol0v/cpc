"""Главное окно стенда CPC для CMM 21-33-21."""

import json
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtSerialPort import QSerialPortInfo
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox, QPlainTextEdit, QTableWidgetItem, QVBoxLayout

import DISC_INFO
import FAULT_WORDS
import uut_encode
from RS_handler import FaultsBuffer, RsWorker
from arinc_handler import ArincWorker
from fault_buffer_table import FAULT_BUFFER_HEADERS, fault_buffer_row
from nvm_export import build_nvm_workbook
from service_ui import ServiceUi


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def fault_name(code):
    return FAULT_WORDS.FAULT_NAMES[code] if 0 <= code < len(FAULT_WORDS.FAULT_NAMES) else '—'


class MainWindow(QtWidgets.QMainWindow):
    sig_connect_arinc_port = pyqtSignal(str)
    sig_connect_rs_port = pyqtSignal(str)
    sig_change_ofv = pyqtSignal(bool, bool, int)
    sig_r_nvram = pyqtSignal(bool, int)
    sig_w_nvram = pyqtSignal(bool, int, int)
    sig_change_uut_in_words = pyqtSignal(dict)
    sig_refresh_bite = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = ServiceUi()
        self.ui.setup(self)
        self.fault_buffers = []
        self.bite_matrix = None
        self.arinc_last_rx_ms = None
        self.rs_last_rx_ms = None
        self.clock = QtCore.QElapsedTimer()
        self.clock.start()

        self.ports_path = os.path.join(BASE_DIR, 'ports.json')
        try:
            with open(self.ports_path, encoding='utf-8') as file:
                ports = json.load(file)
        except (OSError, ValueError):
            ports = {}
        self.arinc_port_name = ports.get('arinc-com', '')
        self.rs_port_name = ports.get('rs-422', '')
        self._requested_arinc_port = self.arinc_port_name
        self._pending_rs_port = None
        self.ui.arinc_connection.setText(f'○  ARINC  ·  {self.arinc_port_name or "not set"} · offline')
        self.ui.rs_connection.setText(f'○  RS-422  ·  {self.rs_port_name or "not set"} · offline')
        self.refresh_ports()
        self.ui.refresh_ports.clicked.connect(self.refresh_ports)
        self.ui.arinc_port_select.currentIndexChanged.connect(self.select_arinc_port)
        self.ui.rs_port_select.currentIndexChanged.connect(self.select_rs_port)
        self.ui.arinc_reconnect.clicked.connect(self.select_arinc_port)
        self.ui.rs_reconnect.clicked.connect(self.select_rs_port)

        self.arinc_thread = QThread(self)
        self.arinc_handler = ArincWorker(self.arinc_port_name)
        self.arinc_handler.moveToThread(self.arinc_thread)
        self.rs_thread = QThread(self)
        self.rs_handler = RsWorker()
        self.rs_handler.moveToThread(self.rs_thread)

        self.arinc_thread.started.connect(self.arinc_handler.slot_connect)
        self.sig_connect_arinc_port.connect(self.arinc_handler.slot_connect_port)
        self.sig_change_uut_in_words.connect(self.arinc_handler.slot_change_uut_word)
        self.arinc_handler.sig_connected.connect(self.slot_arinc_connected)
        self.arinc_handler.sig_port_verified.connect(self.slot_arinc_port_verified)
        self.arinc_handler.sig_port_failed.connect(self.slot_arinc_port_failed)
        self.arinc_handler.sig_bus_activity.connect(self.slot_bus_activity)
        self.arinc_handler.sig_output_word.connect(self.slot_output_word)
        self.arinc_handler.sig_error.connect(self.slot_handler_error)

        self.rs_thread.started.connect(self.rs_handler.start)
        self.sig_connect_rs_port.connect(self.rs_handler.slot_connect_port)
        self.sig_r_nvram.connect(self.rs_handler.slot_read)
        self.sig_w_nvram.connect(self.rs_handler.slot_write)
        self.sig_change_ofv.connect(self.rs_handler.slot_bite_change)
        self.sig_refresh_bite.connect(self.rs_handler.poll_bite_matrix)
        self.rs_handler.sig_rw_reply.connect(self.slot_rw_reply)
        self.rs_handler.sig_bite_matrix.connect(self.show_bite_matrix)
        self.rs_handler.sig_bite_unavailable.connect(self.show_bite_unavailable)
        self.rs_handler.sig_progress_read_buffs.connect(self.slot_read_progress)
        self.rs_handler.sig_show_fbuffs.connect(self.show_fbuffs)
        self.rs_handler.sig_error.connect(self.slot_handler_error)
        self.rs_handler.handler.sig_normal_resp.connect(self.slot_ofv_reply)
        self.rs_handler.handler.sig_response_received.connect(self.slot_rs_packet)
        self.rs_handler.handler.sig_port_opened.connect(self.slot_rs_port_opened)
        self.rs_handler.handler.sig_port_closed.connect(self.slot_rs_port_closed)
        self.rs_handler.sig_port_failed.connect(self.slot_rs_port_failed)

        self.ui.bite_refresh.clicked.connect(self.sig_refresh_bite.emit)
        self.ui.bite_search.textChanged.connect(self.filter_bite)
        self.ui.bite_filter.currentIndexChanged.connect(self.filter_bite)
        self.ui.bite_table.currentCellChanged.connect(self.show_bite_detail)
        self.ui.read_buffers.clicked.connect(self.rs_handler.read_fbuffs)
        self.ui.export_xlsx.clicked.connect(self.save_xlsx)
        self.ui.buffer_search.textChanged.connect(self.filter_buffers)
        self.ui.buffer_table.currentCellChanged.connect(self.show_buffer_detail)
        self.ui.buffer_table.cellDoubleClicked.connect(self.open_buffer_record)
        self.ui.buffer_fields.cellDoubleClicked.connect(self.open_buffer_field)
        self.ui.open_record.clicked.connect(self.open_selected_record)
        self.ui.read_button.clicked.connect(self.read_manual)
        self.ui.write_button.clicked.connect(self.write_manual)
        self.ui.reset_defaults.clicked.connect(self.restore_defaults)
        self.ui.send_ofv.clicked.connect(self.send_ofv)

        self._build_bite_rows()
        self.restore_defaults()
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(500)
        self.activity_timer.timeout.connect(self.refresh_activity)
        self.activity_timer.start()
        self.arinc_thread.start()
        self.rs_thread.start()

    def _build_bite_rows(self):
        table = self.ui.bite_table
        for code, name in enumerate(FAULT_WORDS.FAULT_NAMES):
            table.setItem(code, 0, QTableWidgetItem(f'{code:03d}'))
            table.setItem(code, 1, QTableWidgetItem(name))
            table.setItem(code, 2, QTableWidgetItem('—'))
        table.selectRow(0)

    def filter_bite(self, *_):
        term = self.ui.bite_search.text().strip().lower()
        mode = self.ui.bite_filter.currentText()
        for code, name in enumerate(FAULT_WORDS.FAULT_NAMES):
            active = bool(self.bite_matrix is not None and self.bite_matrix & (1 << code))
            matches = not term or term in f'{code:03d} {name}'.lower()
            if mode == 'Active':
                matches &= active
            elif mode == 'Clear':
                matches &= self.bite_matrix is not None and not active
            self.ui.bite_table.setRowHidden(code, not matches)

    @pyqtSlot(object)
    def show_bite_matrix(self, matrix):
        self.bite_matrix = matrix
        self.rs_last_rx_ms = self.clock.elapsed()
        self.refresh_activity()
        self.ui.bite_status.setText(f'{matrix.bit_count()} active fault(s) · current 14-byte matrix')
        for code in range(len(FAULT_WORDS.FAULT_NAMES)):
            active = bool(matrix & (1 << code))
            item = self.ui.bite_table.item(code, 2)
            item.setText('ACTIVE' if active else 'Clear')
            item.setForeground(QColor('#ad4b19' if active else '#27815a'))
        self.filter_bite()
        self.show_bite_detail(self.ui.bite_table.currentRow(), 0)

    @pyqtSlot(str)
    def show_bite_unavailable(self, reason):
        self.bite_matrix = None
        self.ui.bite_status.setText(f'Matrix unavailable: {reason}')
        for code in range(len(FAULT_WORDS.FAULT_NAMES)):
            self.ui.bite_table.item(code, 2).setText('—')
        self.filter_bite()
        self.show_bite_detail(self.ui.bite_table.currentRow(), 0)

    def show_bite_detail(self, row, _column, *_):
        if not 0 <= row < len(FAULT_WORDS.FAULT_NAMES):
            return
        self.ui.bite_detail_title.setText(f'{row:03d} · {fault_name(row)}')
        state = 'Current state unavailable' if self.bite_matrix is None else (
            'ACTIVE' if self.bite_matrix & (1 << row) else 'Clear')
        self.ui.bite_detail_state.setText(f'Matrix bit {row:03d}: {state}')
        word = next(name for name, first in FAULT_WORDS.WORD_START_CODES.items()
                    if first <= row < first + 16)
        self.ui.bite_detail_source.setText(
            f'{word} · bit {row - FAULT_WORDS.WORD_START_CODES[word]}\n'
            'CMM 21-33-21 · BIT Fault Matrix · 14 bytes')

    @pyqtSlot(str, int)
    def slot_output_word(self, label_octal, word):
        self.arinc_last_rx_ms = self.clock.elapsed()
        self.refresh_activity()
        if label_octal in ('057', '060'):
            number = 1 if label_octal == '057' else 2
            # В выходном слове ARINC доступны только биты данных 11–29.
            value = (word >> 10) & 0x7FFFF
            self.ui.disc_hex[number].setText(f'ARINC word {word:08X}H · SSM {(word >> 29) & 3:02b}')
            for row, (bits, name, setting) in enumerate(DISC_INFO.decode_disc_info(number, value)):
                last_bit = int(bits.split('–')[-1])
                values = (bits, name, setting if last_bit <= 19 else '—')
                for col, text in enumerate(values):
                    self.ui.disc_tables[number].setItem(row, col, QTableWidgetItem(text))
        elif label_octal in ('107', '127'):
            decoded = ArincWorker._decode_bnr(word, lsb_bit=13, resolution=1.0)
            self.ui.output_labels[label_octal].setText(f'{decoded["value"]:,.0f} ft · SSM {decoded["ssm"]:02b}')
        elif label_octal == '270':
            self.ui.output_labels['270'].setText(f'{(word >> 10) & 0x7FFFF:05X}H · SSM {(word >> 29) & 3:02b}')

    @pyqtSlot(dict)
    def slot_bus_activity(self, active):
        if any(active.values()):
            self.arinc_last_rx_ms = self.clock.elapsed()
        self.refresh_activity()

    @pyqtSlot(tuple)
    def slot_ofv_reply(self, positions):
        self.rs_last_rx_ms = self.clock.elapsed()
        self.ui.output_labels['ofv'].setText(f'{positions[0]}° commanded')
        self.refresh_activity()

    @pyqtSlot(bytes)
    def slot_rs_packet(self, _packet):
        self.rs_last_rx_ms = self.clock.elapsed()
        self.refresh_activity()

    @pyqtSlot(str)
    def slot_rs_port_opened(self, name):
        if name == self._pending_rs_port:
            self._save_port('rs-422', name)
            self.rs_port_name = name
            self._pending_rs_port = None
            self.ui.port_message.setText(f'RS-422 port opened: {name}')
        self.ui.rs_connection.setText(f'●  RS-422  ·  {name}')
        self.ui.rs_connection.setStyleSheet('color: #8be0bb;')

    def refresh_activity(self):
        now = self.clock.elapsed()
        arinc_on = self.arinc_last_rx_ms is not None and now - self.arinc_last_rx_ms < 2000
        rs_on = self.rs_last_rx_ms is not None and now - self.rs_last_rx_ms < 3000
        self.ui.arinc_activity.setText('●  ARINC 429  ·  RECEIVING' if arinc_on else '○  ARINC 429  ·  NO OUTPUT')
        self.ui.rs_activity.setText('●  RS-422  ·  ACTIVE' if rs_on else '○  RS-422  ·  NO RESPONSE')
        self.ui.arinc_activity.setStyleSheet(f'color: {"#16805d" if arinc_on else "#a45c25"};')
        self.ui.rs_activity.setStyleSheet(f'color: {"#16805d" if rs_on else "#a45c25"};')

    def restore_defaults(self):
        words = uut_encode.default_uut_in_words()
        self.ui.input_table.setRowCount(len(words))
        for row, (label_octal, value) in enumerate(words.items()):
            self.ui.input_table.setItem(row, 0, QTableWidgetItem(label_octal))
            self.ui.input_table.setItem(row, 1, QTableWidgetItem(value))
        self.sig_change_uut_in_words.emit(words)
        self.ui.ofv_position.setText('50')
        self.ui.ofv_state.setCurrentIndex(1)
        self.ui.ofv_bite.setCurrentIndex(0)
        self.send_ofv()

    def send_ofv(self):
        try:
            position = int(self.ui.ofv_position.text())
            if not -2 <= position <= 122:
                raise ValueError
        except ValueError:
            self.slot_handler_error('OFV position must be an integer from -2 to 122 degrees.')
            return
        self.sig_change_ofv.emit(bool(self.ui.ofv_state.currentIndex()),
                                 bool(self.ui.ofv_bite.currentIndex()), position)

    def _hex_input(self, widget, maximum, name):
        try:
            value = int(widget.text().strip(), 16)
            if not 0 <= value <= maximum:
                raise ValueError
            return value
        except ValueError:
            self.slot_handler_error(f'{name} must be hexadecimal in range 0000–{maximum:04X}.')
            return None

    def read_manual(self):
        address = self._hex_input(self.ui.read_address, 0xFFFF, 'Address')
        if address is not None:
            self.ui.read_reply.clear()
            self.sig_r_nvram.emit(self.ui.read_mode.currentIndex() == 0, address)

    def write_manual(self):
        address = self._hex_input(self.ui.write_address, 0xFFFF, 'Address')
        byte = self.ui.write_mode.currentIndex() == 0
        data = self._hex_input(self.ui.write_data, 0xFF if byte else 0xFFFF, 'Data')
        if address is not None and data is not None:
            self.ui.write_reply.clear()
            self.sig_w_nvram.emit(byte, address, data)

    @pyqtSlot(int, str)
    def slot_rw_reply(self, write, reply):
        self.rs_last_rx_ms = self.clock.elapsed()
        (self.ui.write_reply if write else self.ui.read_reply).setText(reply)

    @pyqtSlot(int)
    def slot_read_progress(self, percent):
        self.ui.progress_bar.setValue(percent)
        count = min(RsWorker.FAULT_BUFFER_COUNT, round(percent * RsWorker.FAULT_BUFFER_COUNT / 100))
        self.ui.progress_label.setText(f'{count} / {RsWorker.FAULT_BUFFER_COUNT} buffers')
        self.ui.read_buffers.setEnabled(percent == 100 or percent == 0)

    @pyqtSlot(list)
    def show_fbuffs(self, buffers):
        self.fault_buffers = buffers
        table = self.ui.buffer_table
        table.setRowCount(len(buffers))
        for row, buffer in enumerate(buffers):
            values = (row, f'{RsWorker.FAULT_MEMORY_START + row * FaultsBuffer.SIZE * 2:04X}H',
                      f'{buffer.fault_code:03d}', fault_name(buffer.fault_code), buffer.flight_leg_counter)
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(str(value)))
        self.filter_buffers()
        if buffers:
            table.selectRow(0)

    def filter_buffers(self, *_):
        term = self.ui.buffer_search.text().strip().lower()
        for row in range(self.ui.buffer_table.rowCount()):
            values = ' '.join(self.ui.buffer_table.item(row, col).text() for col in range(5))
            self.ui.buffer_table.setRowHidden(row, bool(term and term not in values.lower()))

    def show_buffer_detail(self, row, _column, *_):
        if not 0 <= row < len(self.fault_buffers):
            return
        buffer = self.fault_buffers[row]
        self.ui.buffer_summary.setText(
            f'Buffer {row} · {RsWorker.FAULT_MEMORY_START + row * FaultsBuffer.SIZE * 2:04X}H\n'
            f'Fault {buffer.fault_code:03d} · {fault_name(buffer.fault_code)}')
        values = fault_buffer_row(row, buffer)
        table = self.ui.buffer_fields
        table.setRowCount(len(values) - 2)
        for i, (field, value) in enumerate(zip(FAULT_BUFFER_HEADERS[2:], values[2:])):
            table.setItem(i, 0, QTableWidgetItem(field))
            table.setItem(i, 1, QTableWidgetItem(str(value)))

    def open_selected_record(self):
        self.open_buffer_record(self.ui.buffer_table.currentRow(), 0)

    def open_buffer_field(self, field_row, _column):
        buffer_index = self.ui.buffer_table.currentRow()
        if not 0 <= buffer_index < len(self.fault_buffers):
            return
        field = FAULT_BUFFER_HEADERS[field_row + 2]
        buffer = self.fault_buffers[buffer_index]
        if field in ('DISC_INFO1', 'DISC_INFO2'):
            number = int(field[-1])
            value = getattr(buffer, field.lower())
            decoded = DISC_INFO.make_disc_info_table(number, value)
        elif field in FAULT_WORDS.WORD_START_CODES:
            value = getattr(buffer, field.lower())
            decoded = FAULT_WORDS.make_fault_word_table(field, value)
        else:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Buffer {buffer_index} · {field}')
        layout = QVBoxLayout(dialog)
        decoded.setParent(dialog)
        layout.addWidget(decoded)
        dialog.adjustSize()
        dialog.exec_()

    def open_buffer_record(self, row, _column):
        if not 0 <= row < len(self.fault_buffers):
            return
        buffer = self.fault_buffers[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Buffer {row} · full record')
        layout = QVBoxLayout(dialog)
        details = QPlainTextEdit()
        details.setReadOnly(True)
        lines = [f'{field}: {value}' for field, value in zip(FAULT_BUFFER_HEADERS, fault_buffer_row(row, buffer))]
        for number in (1, 2):
            value = getattr(buffer, f'disc_info{number}')
            lines += ['', f'DISC_INFO{number}: {value:06X}H']
            lines += [f'  {bit:>5}  {name}: {setting}' for bit, name, setting in DISC_INFO.decode_disc_info(number, value)]
        for name in FAULT_WORDS.WORD_START_CODES:
            value = getattr(buffer, name.lower())
            lines += ['', f'{name}: {value:04X}H']
            lines += [f'  {bit:>5}  {fault}: {setting}' for bit, fault, setting in FAULT_WORDS.decode_fault_word(name, value)]
        raw = self.rs_handler.raw_buffs[row * FaultsBuffer.SIZE:(row + 1) * FaultsBuffer.SIZE]
        if len(raw) == FaultsBuffer.SIZE:
            lines += ['', 'RAW: ' + ' '.join(raw)]
        details.setPlainText('\n'.join(lines))
        layout.addWidget(details)
        dialog.resize(830, 650)
        dialog.exec_()

    def save_xlsx(self):
        expected = RsWorker.FAULT_BUFFER_COUNT * RsWorker.FAULT_BUFFER_SIZE
        if self.ui.progress_bar.value() != 100 or len(self.rs_handler.raw_buffs) != expected:
            self.slot_handler_error('Read all fault buffers before exporting.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export NVM',
                                              os.path.expanduser('~/moduleCPC_NVM.xlsx'),
                                              'Excel Files (*.xlsx)')
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        try:
            build_nvm_workbook(self.rs_handler.raw_buffs).save(path)
        except Exception as exc:
            self.slot_handler_error(f'Could not export NVM: {exc}')

    def refresh_ports(self):
        available = {info.portName(): info.description() for info in QSerialPortInfo.availablePorts()}
        for selector, saved in ((self.ui.arinc_port_select, self.arinc_port_name),
                                (self.ui.rs_port_select, self.rs_port_name)):
            selected = selector.currentData() or saved
            selector.blockSignals(True)
            selector.clear()
            selector.addItem('Select port', '')
            for name in sorted(set(available) | ({saved} if saved else set())):
                description = available.get(name)
                title = f'{name} — {description}' if description else name
                if name not in available:
                    title += ' (not detected)'
                selector.addItem(title, name)
            index = selector.findData(selected)
            selector.setCurrentIndex(index if index >= 0 else 0)
            selector.blockSignals(False)
        self.ui.port_message.setText(f'{len(available)} port(s) available')

    def select_arinc_port(self, *_):
        name = self.ui.arinc_port_select.currentData()
        if not name:
            return
        self._requested_arinc_port = name
        self.ui.arinc_connection.setText(f'○  ARINC  ·  {name} · checking')
        self.ui.arinc_connection.setStyleSheet('color: #cbd8e9;')
        self.ui.port_message.setText(f'Checking ARINC adapter on {name}...')
        self.sig_connect_arinc_port.emit(name)

    def select_rs_port(self, *_):
        name = self.ui.rs_port_select.currentData()
        if not name:
            return
        self._pending_rs_port = name
        self.ui.port_message.setText(f'Opening RS-422 on {name}...')
        self.sig_connect_rs_port.emit(name)

    def _save_port(self, key, name):
        try:
            with open(self.ports_path, encoding='utf-8') as file:
                ports = json.load(file)
            ports[key] = name
            with open(self.ports_path, 'w', encoding='utf-8') as file:
                json.dump(ports, file, ensure_ascii=False, indent=2)
                file.write('\n')
        except (OSError, ValueError) as exc:
            self.slot_handler_error(f'Port opened, but settings could not be saved: {exc}')

    @pyqtSlot(str)
    def slot_arinc_port_verified(self, name):
        if name != self._requested_arinc_port:
            return
        self._save_port('arinc-com', name)
        self.arinc_port_name = name
        self.ui.arinc_connection.setText(f'●  ARINC  ·  {name}')
        self.ui.arinc_connection.setStyleSheet('color: #8be0bb;')
        self.ui.port_message.setText(f'ARINC connected: {name}')

    @pyqtSlot(str, str)
    def slot_arinc_port_failed(self, name, reason):
        if name != self._requested_arinc_port:
            return
        self.ui.arinc_connection.setText(f'○  ARINC  ·  {name} · offline')
        self.ui.arinc_connection.setStyleSheet('color: #cbd8e9;')
        self.ui.port_message.setText(f'ARINC {name}: {reason}')

    @pyqtSlot()
    def slot_rs_port_closed(self):
        self.ui.rs_connection.setText(f'○  RS-422  ·  {self.rs_port_name or "not set"} · offline')
        self.ui.rs_connection.setStyleSheet('color: #cbd8e9;')

    @pyqtSlot(str, str)
    def slot_rs_port_failed(self, name, reason):
        if name != self._pending_rs_port:
            return
        self._pending_rs_port = None
        self.ui.port_message.setText(f'RS-422 {name}: {reason}')
        selector = self.ui.rs_port_select
        selector.blockSignals(True)
        index = selector.findData(self.rs_port_name)
        selector.setCurrentIndex(index if index >= 0 else 0)
        selector.blockSignals(False)

    @pyqtSlot()
    def slot_arinc_connected(self):
        self.ui.port_message.setText('ARINC adapter verified')

    @pyqtSlot(str)
    def slot_handler_error(self, error):
        QMessageBox.critical(self, 'Error', error)

    def closeEvent(self, event):
        self.arinc_thread.quit()
        self.rs_thread.quit()
        self.arinc_thread.wait(2000)
        self.rs_thread.wait(2000)
        super().closeEvent(event)
