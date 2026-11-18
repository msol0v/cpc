"""Расшифровка семи 16-битных слов журнала по таблице 1018 СММ."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


# В таблице 1018 первое слово названо SYS_FAULT_WORD, в буфере — DCPCS_FAULT_WORD.
WORD_START_CODES = {
    'DCPCS_FAULT_WORD': 0,
    'EXT_SYS_FAULT_WORD': 16,
    'CTR_FAULT_WORD1': 32,
    'CTR_FAULT_WORD2': 48,
    'OFV_FAULT_WORD1': 64,
    'OFV_FAULT_WORD2': 80,
    'PNL_FAULT_WORD1': 96,
}

FAULT_NAMES = (
    'AUTO_CHANNEL_FAIL',
    'COMM_PNL_CTR_FAIL',
    'CTR_OFV_INTERCONNECT_FAIL',
    'LOW_CAB_PRESS_FAIL',
    'DIFF_CAB_PRESS_FAIL',
    'HIGH_CAB_RATE_FAIL',
    'ELACT_STATE_OF_OPER_FAIL',
    'LOOP_CLOSURE_FAIL',
    'AUTO/ALTN/MAN_FAIL',
    'RVT_CALIBRATION_FAIL',
    'SLEW_RATE_FAIL',
    'MOTION_TEST_FAIL',
    'NOT USED',
    'MASTER_SLAVE_DISAGREE_FAIL',
    'AUTO_UNDER_TEST_IN_FAIL',
    'RS422_OFV_TO_CTR_ACTIVITY_FAIL',
    'PNL_SEVER_OPEN_FAIL',
    'CABIN_10000FT_MESSAGE_FG',
    'CABIN_13500FT_MESSAGE_FG',
    'RS422_OFV_TO_CTR_MESSAGE_FAIL_FG',
    'OK_PNL_CTR_MISMATCH_FAIL_FG',
    'CONNECT_ACT_CTR_MISMATCH_FAIL_FG',
    'CAS1_FAIL_FG',
    'CAS2_FAIL_FG',
    'DADC1_FAIL_FG',
    'DADC2_FAIL_FG',
    'SMC1_FAIL_FG',
    'SMC2_FAIL_FG',
    'LDG_GEAR_DISAGREE_FAIL_FG',
    'N1/N2_LOW_FAIL_FG',
    'INFLOW_LEAKAGE_FAIL_FG',
    'AC_RATE_HIGH_FAIL_FG',
    'NOT USED',
    'RAM_REG_FAIL_FG',
    'RAM_EXT_FAIL_FG',
    'PROM_CRC_FAIL_FG',
    'NOT USED',
    'V15_POS_NEG_FAIL_FG',
    'ADC_5V_REF_FAIL_FG',
    'RS422_XMIT_FAIL_FG',
    'RS422_WA_FAIL_FG',
    'ARINC_XMIT_FAIL_FG',
    'WATCHDOG_EXPIRED_FG',
    'ARINC_WA1_FAIL_FG',
    'ARINC_WA2_FAIL_FG',
    'ARINC_WA3_FAIL_FG',
    'NVM_WR_RD_FAIL',
    'NVM_RANGE_FAIL_FG',
    'SENSOR_EEPROM_FAIL_FG',
    'PC_SENSOR_RANGE_FAIL_FG',
    'PRES_REFRESH_FAIL_FG',
    'TEMP_REFRESH_FAIL_FG',
    'PC_VS_PA_FAIL_FG',
    'NOT USED',
    'NOT USED',
    'NOT USED',
    'HSS_OPEN_FAIL_FG',
    'HSS_SHORT_FAIL_FG',
    'RESERVED',
    'OSD_WA_FAIL_FG',
    'AUTO_UNDER_TEST_WA_FAIL_FG',
    'AUTO_OK_WA_FAIL_FG',
    'NOT USED',
    'BCM_FAIL_FG',
    'OFV_RAM_REG_FAIL_FG',
    'OFV_RAM_EXT_FAIL_FG',
    'OFV_INI_RAM_REG_FAIL_FG',
    'OFV_INI_RAM_EXT_FAIL_FG',
    'OFV_MOT_CUR_LIMIT_FAIL_FG',
    'OFV_PWR_EXT_AD_FAIL_FG',
    'LOW_ALT_PRESSURE_SWITCH_FAIL',
    'NOT USED',
    'OFV_PROM_CRC_FAIL_FG',
    'OFV_RS422_WA_FAIL_FG',
    'OFV_RS422_CTR_TO_OFV_ACTIVITY_FAIL',
    'OFV_RS422_XMIT_FAIL_FG',
    'OFV_DISC_WA_FAIL_FG',
    'OFV_RVT_EXC_FAIL_FG',
    'OFV_RVT_POS_FAIL_FG',
    'OFV_B737_ID_STATUS',
    'OFV_AD_TIME_FRAME_FAIL_FG',
    'NOT USED',
    'NOT USED',
    'OFV_ALU_FAIL',
    'NOT USED',
    'NOT USED',
    'NOT USED',
    'OFV_15V_NEG_ADC_FAIL_FG',
    'OFV_HALL_EFF_SEN_FAIL_FG',
    'NOT USED',
    'OFV_CAB_PRESS_SWITCH_STATUS',
    'NOT USED',
    'OFV_ELACT_PROG_PIN_FAIL_FG',
    'NOT USED',
    'NOT USED',
    'NOT USED',
    'PNL_PROM_CRC_FAIL_FG',
    'NOT USED',
    'PNL_NON_DESTRUCTIVE_FAIL_FG',
    'PNL_ALU_FAIL_FG',
    'PNL_ARINC_WA1_FAIL_FG',
    'PNL_ARINC_WA2_FAIL_FG',
    'PNL_A/D_CONVERTER_FAIL_FG',
    'PNL_AUTO_FAIL_WA_FAIL_FG',
    'PNL_UNANTICIPATED_PORING_FAIL_FG',
    'PNL_WATCHDOG_TIMER_FAIL_FG',
    'PNL_RECEIVED_DISCRETE_INPUT_FAIL_FG',
    'PNL_SEVER_VOLTAGE_DROP_HIGH_FAIL',
    'COMM_CTR1_PNL_FAIL_FG',
    'DRIVE_ENABLE_DISAGREE_FAIL_FG',
    'COMM_CTR2_PNL_FAIL_FG',
    'PNL_FAIL_FG',
)


def decode_fault_word(name: str, value: int):
    start_code = WORD_START_CODES[name]
    if not 0 <= value <= 0xFFFF:
        raise ValueError('Fault word must be 16 bits')
    return [
        (str(bit), FAULT_NAMES[start_code + bit], 'TRUE' if value & (1 << bit) else 'FALSE')
        for bit in range(16)
    ]


def make_fault_word_table(name: str, value: int, parent=None):
    rows = decode_fault_word(name, value)
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
    table.setToolTip(f'{name}: {value:04X}H')
    return table
