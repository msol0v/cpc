from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


DISC_INFO1_FIELDS = (
    (1, 1, 'Auto in CTRL', None),
    (2, 2, 'Auto Channel Fail', None),
    (3, 3, 'CTR is Master', None),
    (4, 4, 'Max DP Limit active', None),
    (5, 5, 'Pressure Switch active', None),
    (6, 8, 'Flight Mode', {
        0: 'GROUND', 1: 'TAKE OFF', 2: 'CLIMB', 3: 'ABORT',
        4: 'CRUISE', 5: 'DESCENT',
    }),
    (9, 9, 'DADC#1 used', {0: 'DADC#2 or no DADC used', 1: 'DADC#1 used'}),
    (10, 10, 'SMC#1 used', {0: 'SMC#2 or no SMC used', 1: 'SMC#1 used'}),
    (11, 12, 'OPMODE', {0: 'AUTO', 1: 'ALTN', 2: 'MANUAL', 3: 'unused'}),
    (13, 14, 'CAS Value', {
        0: 'no CAS', 1: 'CAS < 60 kts', 2: '60 ≤ CAS ≤ 100 kts',
        3: 'CAS > 100 kts',
    }),
    (15, 15, 'N1 Value low', {0: 'N1 > 60%', 1: 'N1 ≤ 60% / Invalid'}),
    (16, 16, 'N2 Value low', {0: 'N2 > 89%', 1: 'N2 ≤ 89% / Invalid'}),
    (17, 17, 'B737X_SEL_IN', None),
    (18, 18, 'DADC#1 Inactive', None),
    (19, 19, 'PALT#1 Invalid', None),
    (20, 20, 'CPALT#1 Invalid', None),
    (21, 21, 'CAS#1 Invalid', None),
    (22, 22, 'SMC#1 Inactive', None),
    (23, 23, 'N1#1 Invalid', None),
    (24, 24, 'N2#1 Invalid', None),
)

DISC_INFO2_FIELDS = (
    (1, 'CONNECT_ACT'),
    (2, 'AUTO_UNDER_TEST_IN'),
    (3, 'CARGO_HEAT_VALVE_CLOSED'),
    (4, 'ROC_750_SEL'),
    (5, 'ROD_NOT_350_SEL'),
    (6, 'MASTER_ID'),
    (7, 'MNL_MODE_ACTIVE'),
    (8, 'LEFT_WHEELS_ON_GND'),
    (9, 'RIGHT_WHEELS_ON_GND'),
    (10, 'SHOP_MODE'),
    (11, 'ROD_750_SEL'),
    (12, 'QFE_SEL'),
    (13, 'LEFT_PACK_VALVE_CLOSED'),
    (14, 'RIGHT_PACK_VALVE_CLOSED'),
    (15, 'SLAVE_ID'),
    (16, 'AUTO_IN_CTRL_IN'),
    (17, 'OK_PNL'),
    (18, 'DADC#2 Inactive'),
    (19, 'PALT#2 Invalid'),
    (20, 'CPALT#2 Invalid'),
    (21, 'CAS#2 Invalid'),
    (22, 'SMC#2 Inactive'),
    (23, 'N1#2 Invalid'),
    (24, 'N2#2 Invalid'),
)


def decode_disc_info(number: int, value: int):
    if number == 1:
        fields = DISC_INFO1_FIELDS
    elif number == 2:
        fields = ((bit, bit, name, None) for bit, name in DISC_INFO2_FIELDS)
    else:
        raise ValueError(f'Unknown DISC_INFO number: {number}')

    result = []
    for first, last, name, meanings in fields:
        bits = str(first) if first == last else f'{first}–{last}'
        field_value = (value >> (first - 1)) & ((1 << (last - first + 1)) - 1)
        if meanings:
            setting = f'{field_value} = {meanings.get(field_value, "не определено")}'
        else:
            setting = 'TRUE' if field_value else 'FALSE'
        result.append((bits, name, setting))
    return result


def make_disc_info_table(number: int, value: int, parent=None):
    rows = decode_disc_info(number, value)
    table = QTableWidget(len(rows), 3, parent)
    table.setHorizontalHeaderLabels(('BIT', 'NAME', 'SETTING'))
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.NoSelection)
    table.setFocusPolicy(Qt.NoFocus)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.setWordWrap(False)
    for row, values in enumerate(rows):
        table.setRowHeight(row, 20)
        for column, text in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(text))
    table.setFixedHeight(table.horizontalHeader().height() + 20 * len(rows) + 2 * table.frameWidth())
    table.setFixedWidth(sum(table.columnWidth(column) for column in range(3)) + 2 * table.frameWidth())
    table.setToolTip(f'DISC_INFO{number}: {value:06X}H')
    return table
