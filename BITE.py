import numpy as np

#InMemoryFaultMatrix = np.zeros(6, 19)

BASE_FAULT_CODE_104=0
BASE_FAULT_CODE_105=19
BASE_FAULT_CODE_106=38
BASE_FAULT_CODE_107=57
BASE_FAULT_CODE_110=76
BASE_FAULT_CODE_111=95

class FaultBit():
    """
    Класс содержит всю информацию об ошибке из таблицы 1040, но не содержит значение
    Нужен для отрисовки списка
    """
    def __init__(self, code:int, name:str, fclass:int=0, cause:str='', descriptor:str=''):
        self.code = code
        self.name = name
        self.fault_class = fclass
        self.cause = cause
        self.descriptor = descriptor

Faults = [] # Список FaultBit последовательно как в таблицу 1040 из СММ

def ConfigureFaultBits (product='not 20791-xxAD'):
    _faults = [
        FaultBit(0,'RAM_FAILED_RAM', 1, 'IC400', 'Non-Destructive Internal RAM Test μC cannot access\nthe internal RAM correctly'),
        FaultBit(1,'RAM_FAILED_REG', 1, 'IC400\nIC702\nIC703', 'Non-Destructive External RAM Test μC cannot access\nthe external RAM correctly'),
        FaultBit(2,'FMS1_DATA_OUT_OF_RANGE', 3, 'External', 'Invalid data from FMS1'),
        FaultBit(3,'FMS2_DATA_OUT_OF_RANGE', 3, 'External', 'Invalid data from FMS2'),
        FaultBit(4,'ACT_STATUS_FAIL', 1, 'OFV Ebox\nA/C Wirin', 'Status (operational or standby) of CPC and dedicated\nEbox do not match'),
        FaultBit(5,'CAL_TIME_OPEN_FAIL', 1, 'defective FDM\ndefective EBox\ndefective AuMot\ndefective Gbox', 'OFV does not open within the specified time frame'),
    ]

    Faults.extend(_faults)

    if 'not 20791-xxAD' in product:
        Faults.append(FaultBit(6,'BACKGROUND_TIMEOUT', descriptor='If one run through all background tasks is not finished\nafter 50 seconds this FC is set.'))
        Faults.append(FaultBit(7, 'UNUSED'))
    else:
        Faults.append(FaultBit(6, 'PC_MISMATCH_FAIL', 1))
        Faults.append(FaultBit(7, 'PC_EBOX_FAIL'))

    _faults = [
        FaultBit(8,'ROM_CRC_FAIL', 1, 'IC700\nIC701', 'Calculated Cyclic Redundancy Code differs from stored one.'),
        FaultBit(9,'RS422_WR_FAIL',1,'IC1700\nIC1701', 'RS422 serial link transmitter does not work properly.'),
        FaultBit(10,'RS422_CHECKSUM_FAIL',descriptor='The message identifier, the intermediate characters and\n'
                                                     'checksum are checked by comparing the transmitted\n'
                                                     'message to the checksum calculated in the receiver\nroutine.'),
        FaultBit(11,'CAL_TIME_CLOSE_FAIL',1,'defective FDM\ndefective EBox\ndefective AuMot\ndefective Gbox', 'OFV does not close within the specified time frame'),
        FaultBit(12,'WDT_EXPIRED_FAIL',1, descriptor='CPC was reset due to watchdog timer reset'),
        FaultBit(13, 'PC_STEP_FAIL', 1, 'defective pressure\nransducer\nIC600', 'Cabin pressure changes in an unrealistic way.'),
        FaultBit(14, 'ADIRS1_DATA_OUT_OF_RANGE', 3, 'External', 'Invalid data from ADIRS1'),
        FaultBit(15, 'ADIRS2_DATA_OUT_OF_RANGE', 3, 'External', 'Invalid data from ADIRS2')
    ]

    Faults.extend(_faults)

    if 'not 20791-xxAD' in product:
        Faults.append(FaultBit(16,'A/D_FRAME_COMPLETED_LATE_FAIL', descriptor='If the sum of the A/D conversion times of all A/D chan-\n'
                                                                              'nels requested serially is too long, set fault code flag\n16.'))
    else:
        Faults.append(FaultBit(16, 'UNUSED'))

    _faults = [
        FaultBit(17, 'EIU_SIGNAL_REPLACED', 3, descriptor='Flight mode has been changed irregularly'),
        FaultBit(18, 'ZCAL_FAIL'),
        FaultBit(19, 'ADIRS1_FAIL', 3, 'External', 'No data from ADIRS1'),
        FaultBit(20, 'ADIRS2_FAIL', 3, 'External', 'No data from ADIRS2'),
        FaultBit(21, 'ADIRS3_FAIL', 3, 'External', 'No data from ADIRS3'),
        FaultBit(22, 'ARINC_WR_FAIL', 1, 'IC1000\nIC1008\nIC1100\nIC1005\nIC900', 'More than 2 wraparounds failed.'),
        FaultBit(23, 'RS422_ACTIVITY_FAIL', descriptor='If no serial interrupts from RS422 link for 15 consecu\ntive error counter cycles then set fault code flag 23.'),
        FaultBit(24, 'SLEW_RATE_CLOSE_FAIL', 3),
        FaultBit(25, 'ZCAL_OPEN_FAIL', 1, 'defective FDM\ndefective Ebox', 'Difference between nominal and sensed open position\nis out of range.'),
        FaultBit(26, 'ZCAL_CLOSE_FAIL', 1, 'defective FDM\ndefective Ebox', 'Difference between nominal and sensed close position\nis out of range.'),
        FaultBit(27, 'ADIRS3_DATA_OUT_OF_RANGE', 3, 'External', 'Invalid data from ADIRS3'),
        FaultBit(28, 'STATE_CHANGE_DURING_SCBIT',descriptor='If a state change occurs during the performance of\nSCBIT, set fault code flag 28.'),
        FaultBit(29, 'SCBIT_START_FAIL', 3, 'OFV', 'OFV does not open during SCBIT'),
        FaultBit(30, 'PC_VERSUS_PA_FAIL', 1, descriptor='This test shall compare the calculated cabin pressure\n'
                                                        'PC with the ambient pressure PA received from ADIRS\n during IBIT.')
    ]

    Faults.extend(_faults)

    if 'not 20791-xxAD' in product:
        Faults.append(FaultBit(31, 'UNUSED'))
    else:
        Faults.append(FaultBit(31, 'PC_EBOX_VERSUS_PA_FAIL', 2))

    _faults = [
        FaultBit(32, 'SYSTEM_FAIL', descriptor='This flag is activated with every Class I failure or if all\nthree ADIRS_FAILs have been triggered.'),
        FaultBit(33, 'OFV_BETA_FAIL', 1, 'defective FDM\ndefective Ebox', 'The sensed OFV position does not match with the\naircraft altitude.'),
        FaultBit(34, 'HIGH_CABIN_RATE_FAIL', 1, 'defective pressure\ntransducer\nIC600\nIC601'),
        FaultBit(35, 'LGCIU_SIGNAL_REPLACED', 3, descriptor='During change of flight mode the landing gear signal\nfrom the LGCIU has been replaced'),
        FaultBit(36, '+15V_POWER_FAIL', 1 , 'IC1800', '+15 V cannot be supplied correctly'),
        FaultBit(37, '-15V_POWER_FAIL', 1, 'IC1800', '-15 V cannot be supplied correctly'),
        FaultBit(38, 'AD_CONVERTER_FAIL', 1, 'IC600', 'Conversion of analog signals into digital cannot be per-\nformed in a correct manner.'),
        FaultBit(39, 'CFDS_WR_FAIL', 3, descriptor='All ARINC multiplexers are switched in wraparound position simultaneously and checked one after the other\n'
                                                   'during one routine. The check compares the bit patterns\n'
                                                   'sent out and received back.'),
        FaultBit(40, 'PASS_SIGN_WR_FAIL', 3, descriptor='If discrete output PASS_SIGN and discrete input\n'
                                                        'PASS_SIGN_WR do not match for 10 consecutive error\n'
                                                        'counter cycles then set fault code flag 40.'),
        FaultBit(41, 'FAULT_WARN_WR_FAIL', 1, 'IC1604', 'Fault Warn Light discrete line does not work correctly.'),
        FaultBit(42, 'PC_CAL_ROM_FAIL', 1, 'Pressure Sensor\nIC500', 'Calibration data for the pressure sensor is corrupted.'),
        FaultBit(43, 'NVM_FAIL', 1, descriptor='Checks integrity of NVM chips.'),
        FaultBit(44, 'CFDS_BUS_FAIL', descriptor='If the controller does not receive label 227 (BITE COM-\n'
                                                 'MAND WORD) for 1 second CFDS_BUS_FAIL is set.'),
        FaultBit(45, 'ADIRS1_WR_FAIL', 3, descriptor='If the patterns sent out and received back via ADIRS1\n'
                                                     'do not match for three consecutive times after the multi\n'
                                                     'plexers had been switched and the receivers had been\ncleared this fail is set.'),
        FaultBit(46, 'ADIRS2_WR_FAIL', 3, descriptor='If the patterns sent out and received back via ADIRS2\n'
                                                     ' do not match for three consecutive times after the multi\n'
                                                     ' plexers had been switched and the receivers had been\ncleared this fail is set.'),
        FaultBit(47, 'ADIRS3_WR_FAIL', 3, descriptor='If the patterns sent out and received back via ADIRS3\n'
                                                     ' do not match for three consecutive times after the multi\n'
                                                     ' plexers had been switched and the receivers had been\ncleared this fail is set.'),
        FaultBit(48, 'WDT_TEST_FAIL', 1, descriptor='Watchdog timer does not work properly.'),
        FaultBit(49, 'FMS1_WR_FAIL', 3, descriptor='If the patterns sent out and received back via FMS1 do\n'
                                                   'not match for three consecutive times after the multiplexers had been switched and the receivers had been\n'
                                                   'cleared this fail is set.'),
        FaultBit(50, 'LFES_FAIL', 3, 'LFES', 'During IBIT the controller sends via ARINC bus a message to CFDS which asks the operator to set the LFES\n'
                                             'to the "14000 FT" position. The received analogue voltage is compared to the expected value.'),
        FaultBit(51, 'RS422_FAULT_ISOLATION_CTR_FAIL', 1, 'IC1700\nIC1701', 'The root cause for faulty RS422 communication is loca-\n'
                                                                            'ted within the CPC.'),
        FaultBit(52, 'RS422_FAULT_ISOLATION_ACT_FAIL', 1, 'defective A/C wiring\ndefective Ebox', 'The root cause for faulty RS422 communication is loca-\n'
                                                                                                  'ted within the EBox'),
        FaultBit(53, 'FMS2_WR_FAIL', 3, descriptor='If the patterns sent out and received back via FMS2 do\n'
                                                   'not match for three consecutive times after the multiplexers had been switched and the receivers had been\n'
                                                   'cleared this fail is set.'),
        FaultBit(54, 'FMS1_FAIL', 3, 'External', 'no data from FMS1'),
        FaultBit(55, 'FMS2_FAIL', 3, 'External', 'no data from FMS2'),
        FaultBit(56, '28V_DRIVE_LOW', descriptor='If the voltage at the output of the high side switch drops\n'
                                                 'below nominal 22.5V, the appearance of\n'
                                                 'OFV_LOOP_CLOSURE_FAIL flag received from OFV\n'
                                                 'does not cause a SYSTEM_FAIL. This check is to validate this condition.'),
        FaultBit(57, '+28V_DRIVE_CUT_OFF', descriptor='If the voltage at the output of the high side switch drops\n'
                                                      'below nominal voltage of 16.55 V, the switch is shut off\n'
                                                      'and flag is set'),
        FaultBit(58, 'HSS_OPEN_FAIL', 1, descriptor='Check for a high side switch that does not follow\n'
                                                    ' command to switch power off.'),
        FaultBit(59, 'HSS_SHORT_FAIL', 1, descriptor='Check for a high side switch that does not follow command to switch power on.'),
        FaultBit(60, 'SLEW_RATE_OPEN_FAIL', 3),
        FaultBit(61, 'PC_SENSOR_FAIL', 1, 'Pressure Sensor\nIC600\nIC601', 'Values measured by pressure transducer are beyond\ncertain limits.'),
        FaultBit(62, 'SCBIT_OPEN_FAIL', 3, descriptor='OFV does not open fast enough during SCBIT.'),
        FaultBit(63, 'SCBIT_CLOSE_FAIL', 3, descriptor='OFV does not close fast enough during SCBIT.'),
        FaultBit(64, 'OFV_RAM_FAIL_RAM', 1, 'defective Ebox', 'OFV Non-Destructive Internal RAM Test Ebox μC cannot\naccess the internal RAM correctly'),
        FaultBit(65, 'OFV_RAM_FAIL_REG', 1, 'defective Ebox', 'OFV Non-Destructive External RAM Test Ebox μC cannot\naccess the external RAM correctly'),
        FaultBit(66, 'OFV_INIT_RAM_FAIL_REG', 1, 'defective Ebox', 'OFV Destructive Internal RAM Test Ebox μC cannot\naccess the internal RAM correctly'),
        FaultBit(67, 'OFV_INIT_RAM_FAIL_RAM', 1, 'defective Ebox', 'OFV Destructive External RAM Test Ebox μC cannot\naccess the external RAM correctly'),
    ]

    Faults.extend(_faults)

    if 'not 20791-xxAD' in product:
        Faults.append(FaultBit(68, 'UNUSED'))
    else:
        Faults.append(FaultBit(68, 'MOTOR_DRIVER_OVERCURRENT', 1))

    _faults = [
        FaultBit(69, 'UNUSED'),
        FaultBit(70, 'OFV_BACKGROUND_TIMEOUT'),
        FaultBit(71, 'OFV_SIGNPOST_FAIL'),
        FaultBit(72, 'OFV_ROM_CRC_FAIL', 1, 'defective Ebox', 'Calculated Cyclic Redundancy Code differs from stored\none'),
        FaultBit(73, 'OFV_RS422_WR_FAIL', cause='defective Ebox', descriptor='RS422 serial link transmitter of Ebox does not work\nproperly.'),
        FaultBit(74, 'OFV_RS422_ACTIVITY_FAIL', cause='defective Ebox'),
        FaultBit(75, 'OFV_RS422_RCVR_INTR_FAIL', cause='defective Ebox')
    ]
    Faults.extend(_faults)

    if 'P/N 9023-15703-xx' in product:
        Faults.append(FaultBit(76 , 'OFV_DISCRETE_MUX_FAIL', 1, 'defective Ebox', 'μC cannot send motor direction correctly.'))
    elif 'P/N 20790-xxyy' in product:
        Faults.append(FaultBit(76 , 'MOTOR_DIRECTION_WR_FAIL', 1, 'defective Ebox', 'μC cannot send motor direction correctly.'))
    else:
        Faults.append(FaultBit(76, 'UNUSED'))

    _faults = [
        FaultBit(77, 'OFV_SENSOR_EXCITATION_FAIL', 1, 'defective FDM\ndefective Ebox', 'In order to detect failures within the potentiometer excitation\n'
                                                                                       'circuit resp. corresponding power supply,\n'
                                                                                       'the excitation voltage is monitored.'),
        FaultBit(78, 'OFV_SENSOR_RANGE_FAIL', 1, 'defective FDM\ndefective Ebox', 'The Voltage sent by the FDM is out of range.'),
        FaultBit(79, 'OFV_AIRCRAFT_ID'),
        FaultBit(80, 'OFV_A/D_FRAME_LATE_FAIL', cause='defective Ebox'),
        FaultBit(81, 'OFV_LOOP_CLOSURE_FAIL', 1, 'defective EBox\ndefective AMot\ndefective GBx\ndefective A/C wiring', 'OFV does not follow the controller commands.'),
        FaultBit(82, 'OFV_UNUSED_INTR'),
        FaultBit(83, 'OFV_ALU_FAIL', 1, 'defective Ebox', 'The Arithmetic Logics Unit of the Ebox μC is defective.'),
        FaultBit(84, 'OFV_CHAN1_SEL'),
        FaultBit(85, 'UNUSED'),
        FaultBit(86, 'UNUSED'),
        FaultBit(87, 'OFV_A/D_CONVERT_FAIL', 1, 'defective Ebox', 'Output of +15 VDC internal power supply is out of\nrange.'),
        FaultBit(88, 'OFV_HALL_SENSOR_FAIL', 1, 'defective AMot\ndefective Ebox', 'In order to monitor the hall sensors of the motors for\n'
                                                                                  'failure conditions, undefined sensor combinations are\n'
                                                                                  'detected throughout a dynamic counting process.'),
        FaultBit(89, 'OFV_SW_INTR_FAIL'),
        FaultBit(90, 'OFV_CAB_PRESS_SWITCH_ACTIVE', descriptor='Pressure Switch of Ebox (responsible for closing OFV\nabove 14.500 FT) has been active.'),
        FaultBit(91, 'OFV_RS422_MESSAGE_FAIL', cause='defective Ebox'),
        FaultBit(92, 'OFV_AC_PIN_PROG_FAIL')
    ]
    Faults.extend(_faults)

    if 'P/N 20791-xxAD' in product:
        Faults.append(FaultBit(93, 'OFV_PRESS_SENSOR_FAIL', 2))
    else:
        Faults.append(FaultBit(93, 'UNUSED'))

    _faults = [
        FaultBit(94, 'UNUSED'),
        FaultBit(95, 'UNUSED'),
        FaultBit(96, 'EXC_CAB_ALT_WARNING'),
    ]


def test_config():
    ConfigureFaultBits()
    print(f'Len faults: {len(Faults)}\n\n')

    for fault in Faults:
        print(fault)