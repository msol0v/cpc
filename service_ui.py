"""Интерфейс стенда CPC для CMM 21-33-21, построенный средствами PyQt5."""

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtProperty
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from DISC_INFO import decode_disc_info
from FAULT_WORDS import FAULT_NAMES


STYLE = """
QWidget { background: #f5f7fb; color: #17283f; font-size: 12px; }
QFrame#sidebar { background: #111d33; border: 0; }
QFrame#card { background: white; border: 1px solid #dfe6f0; border-radius: 11px; }
QLabel { background: transparent; }
QPushButton { background: white; color: #243754; border: 1px solid #cfd9e7; border-radius: 7px; padding: 7px 12px; }
QPushButton:hover { background: #eaf1ff; border-color: #8eafe1; }
QPushButton:pressed { background: #d7e5ff; border-color: #4d83d1; padding-top: 9px; padding-bottom: 5px; }
QPushButton:disabled { color: #9ba9bb; background: #edf0f5; border-color: #dde3eb; }
QPushButton#primary { background: #2463d3; color: white; border-color: #2463d3; }
QPushButton#primary:hover { background: #1d56bc; border-color: #1d56bc; }
QPushButton#primary:pressed { background: #174693; border-color: #174693; }
QPushButton#nav { background: transparent; border: 0; color: #bdcadc; text-align: left; padding: 12px 15px; }
QPushButton#nav:hover { background: #1b2b47; color: white; }
QPushButton#nav:pressed { background: #2b4770; padding-top: 14px; padding-bottom: 10px; }
QPushButton#nav[active="true"] { background: #213657; color: white; }
QPushButton#nav[active="true"]:hover { background: #2b4770; }
QPushButton#nav[active="true"]:pressed { background: #345581; }
QPushButton#sidebarAction { background: #213657; color: #d9e6f5; border: 1px solid #395475; padding: 6px; }
QPushButton#sidebarAction:hover { background: #2b4770; border-color: #6688b5; }
QPushButton#sidebarAction:pressed { background: #172842; padding-top: 8px; padding-bottom: 4px; }
QComboBox#sidebarPort { background: #213657; color: white; border: 1px solid #395475; }
QTableWidget { background: white; gridline-color: #dfe6f0; border: 0; selection-background-color: #eaf2ff; selection-color: #243754; }
QHeaderView::section { background: #f3f6fa; color: #64758d; border: 0; border-bottom: 1px solid #dfe6f0; padding: 7px; font-weight: bold; }
QLineEdit, QComboBox { background: white; border: 1px solid #cfd9e7; border-radius: 6px; padding: 5px; min-height: 20px; }
QProgressBar { background: #e9eef6; border: 0; height: 14px; text-align: center; }
QProgressBar::chunk { background: #2463d3; }
"""


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._press_depth = 0.0
        self._animation = QPropertyAnimation(self, b"pressDepth", self)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.pressed.connect(self._press)
        self.released.connect(self._release)

    @pyqtProperty(float)
    def pressDepth(self):
        return self._press_depth

    @pressDepth.setter
    def pressDepth(self, value):
        self._press_depth = value
        self.update()

    def _animate(self, target, duration):
        self._animation.stop()
        self._animation.setStartValue(self._press_depth)
        self._animation.setEndValue(target)
        self._animation.setDuration(duration)
        self._animation.start()

    def _press(self):
        self._animate(1.0, 90)

    def _release(self):
        self.pressDepth = max(self._press_depth, 0.45)
        self._animate(0.0, 180)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._press_depth <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(12, 34, 74, round(44 * self._press_depth)))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 7, 7)


def label(text, size=None, bold=False, color=None):
    result = QLabel(text)
    font = result.font()
    if size:
        font.setPointSize(size)
    font.setBold(bold)
    result.setFont(font)
    if color:
        result.setStyleSheet(f"color: {color};")
    return result


def card(title=None):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(17, 15, 17, 15)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, 13, True))
    return frame, layout


def table(headers, stretch_column=1):
    result = QTableWidget(0, len(headers))
    result.setHorizontalHeaderLabels(headers)
    result.verticalHeader().hide()
    result.setEditTriggers(QAbstractItemView.NoEditTriggers)
    result.setSelectionBehavior(QAbstractItemView.SelectRows)
    result.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    if stretch_column is not None:
        result.horizontalHeader().setSectionResizeMode(
            stretch_column, QHeaderView.Stretch
        )
    return result


class ServiceUi:
    def setup(self, window):
        window.setWindowTitle("TEST PANEL SOFTWARE CMM 21-33-21")
        window.resize(1500, 900)
        window.setMinimumSize(1100, 700)
        window.setStyleSheet(STYLE)
        root = QWidget(window)
        window.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(230)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(15, 24, 15, 20)
        sl.setSpacing(8)
        self.nav = []
        self.stack = QStackedWidget()
        for index, name in enumerate(("UUT Output", "BITE", "NVM", "UUT Input")):
            button = AnimatedButton(name)
            button.setObjectName("nav")
            button.setProperty("active", "true" if index == 0 else "false")
            button.clicked.connect(lambda _, i=index: self.select_page(i))
            sl.addWidget(button)
            self.nav.append(button)
        sl.addStretch()
        sl.addWidget(label("CONNECTIONS", 9, True, "#92a4bf"))
        self.rs_connection = label("○  RS-422  ·  offline", 10, color="#cbd8e9")
        self.arinc_connection = label("○  ARINC  ·  offline", 10, color="#cbd8e9")
        sl.addWidget(self.arinc_connection)
        self.arinc_port_select = QComboBox()
        self.arinc_port_select.setObjectName("sidebarPort")
        sl.addWidget(self.arinc_port_select)
        self.arinc_reconnect = AnimatedButton("Connect ARINC")
        self.arinc_reconnect.setObjectName("sidebarAction")
        sl.addWidget(self.arinc_reconnect)
        sl.addSpacing(7)
        sl.addWidget(self.rs_connection)
        self.rs_port_select = QComboBox()
        self.rs_port_select.setObjectName("sidebarPort")
        sl.addWidget(self.rs_port_select)
        self.rs_reconnect = AnimatedButton("Connect RS-422")
        self.rs_reconnect.setObjectName("sidebarAction")
        sl.addWidget(self.rs_reconnect)
        self.refresh_ports = AnimatedButton("Refresh ports")
        self.refresh_ports.setObjectName("sidebarAction")
        sl.addWidget(self.refresh_ports)
        self.port_message = label("", 9, color="#92a4bf")
        self.port_message.setWordWrap(True)
        sl.addWidget(self.port_message)
        outer.addWidget(side)

        self._add_page(self._overview)
        self._add_page(self._bite)
        self._add_page(self._nvm)
        self._add_page(self._bench)
        outer.addWidget(self.stack, 1)

    def select_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav):
            button.setProperty("active", "true" if i == index else "false")
            button.style().unpolish(button)
            button.style().polish(button)

    def _add_page(self, build):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 21, 26, 21)
        layout.setSpacing(14)
        build(layout)
        scroll.setWidget(content)
        self.stack.addWidget(scroll)

    def _heading(self, layout, title, subtitle, actions=()):
        head = QHBoxLayout()
        texts = QVBoxLayout()
        texts.addWidget(label(title, 21, True))
        texts.addWidget(label(subtitle, 10, color="#6b7d95"))
        head.addLayout(texts, 1)
        for action in actions:
            head.addWidget(action)
        layout.addLayout(head)

    def _overview(self, layout):
        self._heading(
            layout,
            "UUT ARINC OUTPUT WORDS",
            "DISC_INFO1 / DISC_INFO2 / other values",
        )
        activity, al = card("Communication activity")
        row = QHBoxLayout()
        self.arinc_activity = label("ARINC 429  ·  waiting for output", 11, True)
        self.rs_activity = label("RS-422  ·  waiting for response", 11, True)
        row.addWidget(self.arinc_activity, 1)
        row.addWidget(self.rs_activity, 1)
        al.addLayout(row)
        layout.addWidget(activity)

        pair = QHBoxLayout()
        pair.setSpacing(12)
        self.disc_tables = {}
        self.disc_hex = {}
        for number, tag in ((1, "057"), (2, "060")):
            panel, pl = card(f"DISC_INFO{number}  ·  label {tag}₈")
            hex_label = label("No output word received", 10, color="#6b7d95")
            self.disc_hex[number] = hex_label
            pl.addWidget(hex_label)
            t = table(("BIT", "FIELD", "VALUE"))
            fields = decode_disc_info(number, 0)
            t.setRowCount(len(fields))
            for row, (bits, name, _setting) in enumerate(fields):
                for column, value in enumerate((bits, name, "—")):
                    t.setItem(row, column, QTableWidgetItem(value))
            self.disc_tables[number] = t
            pl.addWidget(t)
            pair.addWidget(panel, 1)
        layout.addLayout(pair, 1)

        outputs, ol = card("Other")
        grid = QGridLayout()
        self.output_labels = {}
        for i, (tag, title) in enumerate(
            (
                ("107", "107₈ · SCRFL"),
                ("127", "127₈ · SLFE"),
                ("270", "270₈ · CTR_DISC_STAT"),
                ("ofv", "RS-422 · OFV"),
            )
        ):
            grid.addWidget(label(title, 10, True, "#64758d"), 0, i)
            value = label("—", 12, True)
            grid.addWidget(value, 1, i)
            self.output_labels[tag] = value
        ol.addLayout(grid)
        layout.addWidget(outputs)

    def _bite(self, layout):
        self.bite_refresh = AnimatedButton("Refresh")
        self._heading(
            layout, "BITE", "Fault matrix read over RS-422", (self.bite_refresh,)
        )
        self.bite_status = label("Waiting for current matrix", 10, color="#6b7d95")
        layout.addWidget(self.bite_status)
        body = QHBoxLayout()
        list_card, ll = card("Fault codes")
        filters = QHBoxLayout()
        self.bite_search = QLineEdit()
        self.bite_search.setPlaceholderText("Search code or fault name")
        self.bite_filter = QComboBox()
        self.bite_filter.addItems(("All", "Active", "Clear"))
        filters.addWidget(self.bite_search, 1)
        filters.addWidget(self.bite_filter)
        ll.addLayout(filters)
        self.bite_table = table(("CODE", "FAULT NAME", "STATE"))
        self.bite_table.setRowCount(len(FAULT_NAMES))
        ll.addWidget(self.bite_table, 1)
        body.addWidget(list_card, 3)
        details, dl = card("Fault details")
        self.bite_detail_title = label("Select a fault code", 13, True)
        self.bite_detail_state = label("Current matrix not yet read")
        self.bite_detail_source = label(
            "Source: current BIT Fault Matrix · 14 bytes", 9, color="#718198"
        )
        dl.addWidget(self.bite_detail_title)
        dl.addWidget(self.bite_detail_state)
        dl.addStretch()
        dl.addWidget(self.bite_detail_source)
        body.addWidget(details, 2)
        layout.addLayout(body, 1)

    def _nvm(self, layout):
        self.read_buffers = AnimatedButton("Read buffers")
        self.read_buffers.setObjectName("primary")
        self.export_xlsx = AnimatedButton("Export XLSX")
        self._heading(
            layout,
            "NVM",
            "42 buffers · 48 bytes each · historical fault records",
            (self.read_buffers, self.export_xlsx),
        )
        progress, pl = card("Buffer readout")
        self.progress_label = label("0 / 42 buffers")
        pl.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        pl.addWidget(self.progress_bar)
        layout.addWidget(progress)

        body = QHBoxLayout()
        listing, ll = card("Fault buffers")
        self.buffer_search = QLineEdit()
        self.buffer_search.setPlaceholderText("Search code, address or flight leg")
        ll.addWidget(self.buffer_search)
        self.buffer_table = table(
            ("#", "ADDRESS", "CODE", "FAULT NAME", "FLIGHT LEG"), 3
        )
        ll.addWidget(self.buffer_table, 1)
        body.addWidget(listing, 3)
        details, dl = card("Selected buffer")
        self.buffer_summary = label("Read buffers to inspect their fields.")
        self.buffer_summary.setWordWrap(True)
        dl.addWidget(self.buffer_summary)
        self.buffer_fields = table(("FIELD", "VALUE"), 0)
        dl.addWidget(self.buffer_fields, 1)
        self.open_record = AnimatedButton("Open full record")
        dl.addWidget(self.open_record)
        body.addWidget(details, 2)
        layout.addLayout(body, 1)

        tools = QHBoxLayout()
        read, rl = card("Manual NVM read")
        rr = QHBoxLayout()
        rr.addWidget(label("Address"))
        self.read_address = QLineEdit("2084")
        self.read_address.setMaximumWidth(90)
        rr.addWidget(self.read_address)
        self.read_mode = QComboBox()
        self.read_mode.addItems(("Byte", "Word"))
        self.read_mode.setCurrentIndex(1)
        rr.addWidget(self.read_mode)
        self.read_button = AnimatedButton("Read")
        rr.addWidget(self.read_button)
        self.read_reply = QLineEdit()
        self.read_reply.setReadOnly(True)
        self.read_reply.setPlaceholderText("Reply")
        rr.addWidget(self.read_reply, 1)
        rl.addLayout(rr)
        tools.addWidget(read, 1)
        write, wl = card("Manual NVM write")
        wr = QHBoxLayout()
        wr.addWidget(label("Address"))
        self.write_address = QLineEdit()
        self.write_address.setPlaceholderText("Hex")
        self.write_address.setMaximumWidth(80)
        wr.addWidget(self.write_address)
        wr.addWidget(label("Data"))
        self.write_data = QLineEdit()
        self.write_data.setPlaceholderText("Hex")
        self.write_data.setMaximumWidth(80)
        wr.addWidget(self.write_data)
        self.write_mode = QComboBox()
        self.write_mode.addItems(("Byte", "Word"))
        wr.addWidget(self.write_mode)
        self.write_button = AnimatedButton("Write")
        wr.addWidget(self.write_button)
        self.write_reply = QLineEdit()
        self.write_reply.setReadOnly(True)
        self.write_reply.setPlaceholderText("Reply")
        wr.addWidget(self.write_reply, 1)
        wl.addLayout(wr)
        tools.addWidget(write, 1)
        layout.addLayout(tools)

    def _bench(self, layout):
        self._heading(
            layout,
            "Bench setup and input signals",
            "ARINC inputs and RS-422 OFV",
        )
        body = QHBoxLayout()
        inputs, il = card("ARINC 429 · UUT inputs")
        il.addWidget(label("Current transmitted default words", 10, color="#6b7d95"))
        self.input_table = table(("LABEL₈", "WORD HEX"), 1)
        il.addWidget(self.input_table, 1)
        self.reset_defaults = AnimatedButton("Restore default inputs and OFV state")
        il.addWidget(self.reset_defaults)
        body.addWidget(inputs, 3)
        ofv, ol = card("OFV · RS-422")
        form = QGridLayout()
        form.addWidget(label("State"), 0, 0)
        self.ofv_state = QComboBox()
        self.ofv_state.addItems(("Standby 01H", "Operational 02H"))
        form.addWidget(self.ofv_state, 0, 1)
        form.addWidget(label("BITE flag"), 1, 0)
        self.ofv_bite = QComboBox()
        self.ofv_bite.addItems(("Clear", "Set"))
        form.addWidget(self.ofv_bite, 1, 1)
        form.addWidget(label("Position (deg)"), 2, 0)
        self.ofv_position = QLineEdit("50")
        form.addWidget(self.ofv_position, 2, 1)
        ol.addLayout(form)
        self.send_ofv = AnimatedButton("Update")
        self.send_ofv.setObjectName("primary")
        ol.addWidget(self.send_ofv)
        ol.addWidget(
            label(
                "S-message is transmitted every 200 ms after it is set.",
                10,
                color="#6b7d95",
            )
        )
        ol.addStretch()
        body.addWidget(ofv, 2)
        layout.addLayout(body, 1)
