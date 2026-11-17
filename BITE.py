"""BITE fault catalogue for CMM 21-33-20, P/N 7121-19971.

Matrix bit names: Testing and Fault Isolation, pages 1021-1024.
Fault indications and descriptions: Table 5, pages 39-58.
The manual lists no separate Table 5 entry for fault code 000.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FaultBit:
    code: int
    name: str
    auto_fail: str = ""
    nvm: str = ""
    recoverable: str = ""
    fault_indication: str = ""
    descriptor: str = ""
    cmm_page: int | None = None
    reference_name: str = ""


Faults = [
    FaultBit(
        0, 'AUTO_CHANNEL_FAIL_FG',
    ),
    FaultBit(
        1, 'COMM_PNL_CTR_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='A',
        fault_indication='SYSTEM WIRING; Detail: CPC-PNL WIRING',
        descriptor=(
            'This fault code will also be set if a communication fail (no bus activity, parity '
            'error, short/long word, faulty data) is detected by the CTR and the ARINC wraparound '
            'of the CTR and the PNL is passed (fault is isolated to the inter-connect). In this '
            'case auto channel fail will be set and the failure will be autorecoverable.'
        ),
        cmm_page=39,
        reference_name='COMM_PNL_CTR_FAIL',
    ),
    FaultBit(
        2, 'CTR_OFV_INTERCONN_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='SYSTEM WIRING; Detail: CPC/OFV WIRING',
        descriptor=(
            'This fault code will also be set if no RS422 activity is detected by the CTR and the '
            'fault is isolated to the interconnect (CTR RS422 wraparound passed and '
            'CONNECT_ACT_CTR_IN = false). In this case auto channel fail will be set'
        ),
        cmm_page=39,
        reference_name='CTR_OFV INTERCONNECT FAIL',
    ),
    FaultBit(
        3, 'LOW_CAB_PRESS_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='HI CAB ALT',
        descriptor=(
            'System parameter test, indicates a cabin pressure lower than 8 psi and the OFV '
            'position is still above 5 degrees after 1 second.'
        ),
        cmm_page=39,
        reference_name='LOW CAB PRESS FAIL',
    ),
    FaultBit(
        4, 'DIFF_CAB_PRESS_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CAB DIFF PRESS HI',
        descriptor=(
            'System parameter test, indicates a cabin differential pressure greater than 8.3 psi '
            '(for P/N 7121-19971-01BA only: dP > 9.39 psi) with an OFV position of less than 20 '
            'degrees after 5 seconds.'
        ),
        cmm_page=39,
        reference_name='DIFF CAB PRESS FAIL',
    ),
    FaultBit(
        5, 'HIGH_CAB_RATE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CAB RATE HI',
        descriptor=(
            'System parameter test, indicates a cabin pressure rate greater than 2000 SLFPM and the '
            'OFV position is still above 5 degrees after 5 seconds or a cabin pressure rate of less '
            'than -2000 SLFPM and the OFV position is still below 5 degrees after 5 seconds.'
        ),
        cmm_page=39,
        reference_name='HIGH CAB RATE FAIL',
    ),
    FaultBit(
        6, 'ELACT_STATE_OF_OPER_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='SYSTEM WIRING; Detail: CPC-PNL WIRING, PNL-OFV',
        descriptor=(
            'System parameter test, indicates the OFV cannot follow the state of the CTR and the '
            'failure is not isolated to the PNLs sever switch or the CTRs HSS switch. May be caused '
            'by an interconnect failure in the DRIVE_ENABLE_CTR_PNL line, the DRIVE_ENABLE_PNL_ACT '
            'line, the MNL_MODE_PNL_CTR line'
        ),
        cmm_page=40,
        reference_name='ELACT STATE OF OPER FAIL',
    ),
    FaultBit(
        7, 'LOOP_CLOSURE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'System parameter test, indicates that the OFV cannot follow the CTR position command '
            '(OFV_LOOP_CLOSURE_STATUS is set to true) and the OFV position is below 20 degrees.'
        ),
        cmm_page=40,
        reference_name='LOOP CLOSURE FAIL',
    ),
    FaultBit(
        8, 'AUTO/ALTN/MAN_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='AUTO/MAN ERROR',
        descriptor=(
            'System parameter test, indicates that more than one or none of the AUTO, ALTN or '
            'MANUAL indications are received by the CTR.'
        ),
        cmm_page=40,
        reference_name='AUTO/ALTN/MAN FAIL',
    ),
    FaultBit(
        9, 'RVT_CALIBRATION_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='N',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the OFV does not reach the mechanical stop within time '
            'or the calibration constant is out of range. This test is part of the IBIT only. May '
            'be caused by a mechanical blockage/restriction of the OFV or an OFV failure.'
        ),
        cmm_page=40,
        reference_name='RVT CALIBRATION FAIL',
    ),
    FaultBit(
        10, 'SLEW_RATE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='N',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the OFV is not able to drive fully open to fully closed '
            'or vice versa within the given time constrains. This test is part of the IBIT only.'
        ),
        cmm_page=40,
        reference_name='SLEW RATE FAIL',
    ),
    FaultBit(
        11, 'OFV_MOTION_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the OFV is not able to move from fully open to 105 '
            'degrees and back within the give time constrains. This test is part of the SCBIT only.'
        ),
        cmm_page=41,
        reference_name='MOTION TEST FAIL',
    ),
    FaultBit(
        12, 'NOT USED',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR BBJ PIN (for P/N 7121-19971-01BA only)',
        descriptor=(
            'Matrix listing marks bit 012 as NOT USED; Table 5 lists SYSTEM WIRING. This fail flag '
            'will be set if BBJ_SEL_IN is not tied to Ground. May be caused by a wire failure or '
            'connection failure outside of the CTR.'
        ),
        cmm_page=41,
        reference_name='SYSTEM WIRING',
    ),
    FaultBit(
        13, 'MASTER_SLAVE_DISAGREE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='SYSTEM WIRING; Detail: CONTRLR PROG PIN',
        descriptor=(
            'This fail flag will be set if the CTR MASTER/SLAVE pin programming is contradictory. '
            'May be caused by a wire failure or connection failure outside of the CTR.'
        ),
        cmm_page=41,
        reference_name='MASTER/SLAVE DISAGREE',
    ),
    FaultBit(
        14, 'AUTO_UNDER_TEST_FAIL',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='SYSTEM WIRING; Detail: CPC-CPC WIRING',
        descriptor=(
            'This fail flag will be set if the CTR receives consecutively for 5 minutes an '
            'indication that the other CTR performs IBIT while in flight. May be caused by a defect '
            'AUTO_UNDER_TEST wire outside of the CTR which is fed to 28V_RTN.'
        ),
        cmm_page=41,
        reference_name='AUTO_UNDER_TEST_IN_FAIL',
    ),
    FaultBit(
        15, 'RS422_OFV_ACTIVITY_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV OR WIRING',
        descriptor=(
            'This fail flag will be set if the CTR cannot detect OFV RS422 activity and the CTR '
            'RS422 wraparound is passed and the CONNECT_ACT_CTR_IN is true. May be caused by an '
            'ELACT hardware failure or by a CTR_ACT interconnection failure.'
        ),
        cmm_page=41,
        reference_name='RS422_OFV_TO_CTR_ACTIVITY_FAIL',
    ),
    FaultBit(
        16, 'PNL_SEVER_OPEN_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag is set whenever the CTR detects that the PNL was unable to open the '
            'sever switch. The test is performed if a switch from AUTO to MANUAL or from ALTN to '
            'MANUAL is detected (CTRs opmode switched to MANUAL). This test cannot be rerun during '
            'IBIT. Therefore this fail flag is cleared after IBIT even if the failure is still '
            'present.'
        ),
        cmm_page=42,
        reference_name='PNL_SEVER_OPEN_FAIL',
    ),
    FaultBit(
        17, 'NOT USED',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='Cabin Altitude in excess of 10000 ft',
        descriptor=(
            'Matrix listing marks bit 017 as NOT USED; Table 5 lists CABIN 1000 FT MESSAGE FAIL. '
            'This message is set if cabin altitude is above 10000 ft and LFE is less than 9500 ft.'
        ),
        cmm_page=42,
        reference_name='CABIN 1000 FT MESSAGE FAIL',
    ),
    FaultBit(
        18, 'NOT USED',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='Cabin Altitude in excess of 10000 ft',
        descriptor=(
            'Matrix listing marks bit 018 as NOT USED; Table 5 lists CABIN 13500 FT MESSAGE FAIL. '
            'This message is set if cabin altitude is above 13500 ft and LFE is less than 13000 ft.'
        ),
        cmm_page=42,
        reference_name='CABIN 13500 FT MESSAGE FAIL',
    ),
    FaultBit(
        19, 'RS422_OFV_TO_CTR_MESSAGE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the CTR receives faulty data from the OFV for longer '
            'than 3 seconds. This failure may be caused by an ELACT hardware or software failure.'
        ),
        cmm_page=42,
        reference_name='RS422_OFV_TO_CTR_MESSAGE_FAIL',
    ),
    FaultBit(
        20, 'OK_PNL_CTR_MISMATCH_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SYSTEM WIRING; Detail: CPC-PNL WIRING',
        descriptor=(
            'This fault code will be set if a mismatch between the discrete OK_PNL_CTR signal and '
            'the PNL health information on the PNC fault word is detected.'
        ),
        cmm_page=42,
        reference_name='OK_PNL_CTR_MISMATCH',
    ),
    FaultBit(
        21, 'CONNECT_ACT_CTR_MISMATCH_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SYSTEM WIRING; Detail: CPC-OFV WIRING',
        descriptor=(
            'This fault code will be set if a failure of the discrete CONNECT_ACT_CTR line is '
            'detected (RS422 activity is present and CONNECT_ACT_CTR = false).'
        ),
        cmm_page=43,
        reference_name='CONNECT_ACT_CTR_MISMATCH',
    ),
    FaultBit(
        22, 'CAS1_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='DADC # 1 INVALID',
        descriptor=(
            'This fail flag indicates that the CAS received from DADC # 1 is invalid or not '
            'updated.'
        ),
        cmm_page=43,
        reference_name='CAS 1 FAIL',
    ),
    FaultBit(
        23, 'CAS2_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='DADC # 2 INVALID',
        descriptor=(
            'This fail flag indicates that the CAS received from DADC # 2 is invalid or not '
            'updated.'
        ),
        cmm_page=43,
        reference_name='CAS 2 FAIL',
    ),
    FaultBit(
        24, 'DADC1_FAIL_FG',
        auto_fail='0/1',
        nvm='1',
        recoverable='A',
        fault_indication='DADC # 1 INVALID',
        descriptor=(
            'This fail flag is set if no bus activity of DADC1 is detected, pressure altitude or '
            'barocorrected pressure altitude are not received or faulty for longer than 2 seconds. '
            'Auto channel fail will be set if DADC2 FAIL is set too. Auto channel fail will NOT be '
            'set if true air speed only is missing or faulty for longer than 2 seconds.'
        ),
        cmm_page=43,
        reference_name='DADC1 FAIL',
    ),
    FaultBit(
        25, 'DADC2_FAIL_FG',
        auto_fail='0/1',
        nvm='1',
        recoverable='A',
        fault_indication='DADC # 2 INVALID',
        descriptor=(
            'This fail flag is set if no bus activity of DADC2 is detected, pressure altitude or '
            'barocorrected pressure altitude are not received or faulty for longer than 2 '
            'seconds.Auto channel fail will be set if DADC1 FAIL is set too. Auto channel fail will '
            'NOT be set if true air speed only is missing or faulty for longer than 2 seconds.'
        ),
        cmm_page=43,
        reference_name='DADC2 FAIL',
    ),
    FaultBit(
        26, 'SMC1_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='SMC #1 INVALID',
        descriptor=(
            'This fail flag will be set if no bus activity of SMC1 is detected, or N1 value or N2 '
            'value is not received or invalid for longer than 2 seconds. Auto channel fail will be '
            'set if SMC2 FAIL is set too. Auto channel fail will only be set as long as the mode is '
            'GR or TO.'
        ),
        cmm_page=44,
        reference_name='SMC1 FAIL',
    ),
    FaultBit(
        27, 'SMC2_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='SMC #2 INVALID',
        descriptor=(
            'This fail flag will be set if no bus activity of SMC2 is detected, or N1 value or N2 '
            'value is not received or invalid for longer than 2 seconds. Auto channel fail will be '
            'set if SMC1 FAIL is set too. Auto channel fail will only be set as long as the mode is '
            'GR or TO.'
        ),
        cmm_page=44,
        reference_name='SMC2 FAIL',
    ),
    FaultBit(
        28, 'LDG_GEAR_DISAGREE_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='LDG/GEAR DISAGREE',
        descriptor=(
            'This fail flag will be set if a mode switch GR to CI or TO to CI occurs due to '
            'ambiguous landing gears using the condition for true air speed. May be caused by a '
            'failure of the “LEFT_WHEELS_ON_ GND” or “RIGHT_WHEELS_ON_GND” signals outside of the '
            'CTR.'
        ),
        cmm_page=44,
        reference_name='LDG_GEAR_DISAGREE_FAIL',
    ),
    FaultBit(
        29, 'N1/N2_LOW_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='N1/N2 LOW',
        descriptor=(
            'This fail flag will be set if a mode switch GR to CI occurs due to no valid N1 or N2 '
            'value available or a valid N1 or N2 value below the value required for the mode '
            'switch. May be caused by a lower throttle lever setting during take off run or an SMC '
            'fail. Failure is outside of the DCPCS.'
        ),
        cmm_page=44,
        reference_name='N1/N2_LOW_FAIL',
    ),
    FaultBit(
        30, 'INFLOW_LEAKAGE_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='LO INFL/HI LEAKG',
        descriptor=(
            'This fail flag will be set whenever the OFV position is below 3 degrees for longer '
            'than 5 seconds. This is no failure of the DCPCS. May be caused by a low inflow '
            'situation or a high leakage.'
        ),
        cmm_page=44,
        reference_name='INFLOW_LEAKAGE_FAIL',
    ),
    FaultBit(
        31, 'AC_RATE_HIGH_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='ACFT RATE HI',
        descriptor=(
            'This fail flag will be set whenever the cabin rate is above the allowed hardlimit for '
            'more than 5 seconds caused by a high A/C rate in conjunction with maximum dp (7.95 '
            'psi) or negative dp (0.05 psi) is present. This is no failure of the DCPCS.'
        ),
        cmm_page=45,
        reference_name='AC_RATE_HIGH_FAIL',
    ),
    FaultBit(
        32, 'CPC97_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The CPC97 gate array tests detected a failure in the CPC97 gate array.'
        ),
        cmm_page=46,
        reference_name='CPC97_FAIL',
    ),
    FaultBit(
        33, 'RAM_REG_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The non destructive RAM test detected a failure in the internal RAM of the 8097 '
            'microprocessor.'
        ),
        cmm_page=46,
        reference_name='RAM_REG_FAIL',
    ),
    FaultBit(
        34, 'RAM_EXT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The non destructive RAM test detected a failure in the external CTR RAM.'
        ),
        cmm_page=46,
        reference_name='RAM_EXT_FAIL',
    ),
    FaultBit(
        35, 'PROM_CRC_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The Cyclic Redundancy Check detected a failure of the CTR EPROMS. It has to be '
            'assumed, that the software contained in the PROMs is not in an operative condition.'
        ),
        cmm_page=46,
        reference_name='PROM_CRC-FAIL',
    ),
    FaultBit(
        36, 'ALU_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The arithmetic test of the microprocessor detected a failure.'
        ),
        cmm_page=46,
        reference_name='ALU_FAIL',
    ),
    FaultBit(
        37, 'V15_POS_NEG_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The +15 V DC and -15 V DC from the power supply are continuously monitored at an '
            'analog input port of the A/D converter. The fail flag is set if the difference of both '
            'power lines is out of range required to drive the ARINC transmitters.'
        ),
        cmm_page=46,
        reference_name='15V_POS_NEG_FAIL',
    ),
    FaultBit(
        38, 'ADC_5V_REF_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'The A/D converter is continuously tested against +5 V DC via an analog input. If the '
            'measured value differs more than 4% from the nominal value, the fail flag is set.'
        ),
        cmm_page=47,
        reference_name='ADC_5V_REF_FAIL',
    ),
    FaultBit(
        39, 'RS422_XMIT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if no RS422 transmitter interrupt activity is detected.'
        ),
        cmm_page=47,
        reference_name='RS422_XMIT_FAIL',
    ),
    FaultBit(
        40, 'RS422_WA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the CTR RS422 interface fails.'
        ),
        cmm_page=47,
        reference_name='RS422_WA_FAIL',
    ),
    FaultBit(
        41, 'ARINC_XMIT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if no ARINC transmitter interrupt activity is detected.'
        ),
        cmm_page=47,
        reference_name='ARINC_XMIT_FAIL',
    ),
    FaultBit(
        42, 'WATCHDOG_EXPIRED_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the CTR watchdog is not served correctly by the '
            'software. May be caused by a software anomaly.'
        ),
        cmm_page=47,
        reference_name='WATCHDOG_EXPIRED',
    ),
    FaultBit(
        43, 'ARINC_WA1_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the ARINC wraparound of ARINC transmitter circuit 1, MUX '
            '1 and ARINC receiver 1 fails.'
        ),
        cmm_page=47,
        reference_name='ARINC_WA1_FAIL',
    ),
    FaultBit(
        44, 'ARINC_WA2_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the ARINC wraparound of ARINC transmitter circuit 2, MUX '
            '2 and ARINC receiver 2 fails.'
        ),
        cmm_page=48,
        reference_name='ARINC_WA2_FAIL',
    ),
    FaultBit(
        45, 'ARINC_WA3_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the ARINC wraparound of ARINC transmitter circuit 3, MUX '
            '3 and ARINC receiver 3 fails.'
        ),
        cmm_page=48,
        reference_name='ARINC_W3_FAIL',
    ),
    FaultBit(
        46, 'NVM_WR_RD_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if a write to the NVM cannot be performed correctly.'
        ),
        cmm_page=48,
        reference_name='NVM_WR_RD_FAIL',
    ),
    FaultBit(
        47, 'NVM_RANGE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the data read out of the NVM flight buffer or NVM power '
            'down buffer after POR or Pilot Reset is not within the valid range.'
        ),
        cmm_page=48,
        reference_name='NVM_RANGE_FAIL',
    ),
    FaultBit(
        48, 'SENSOR_EEPROM_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the checksum test of the sensor EEPROM data fails.'
        ),
        cmm_page=49,
        reference_name='SENSOR_EEPROM_FAIL',
    ),
    FaultBit(
        49, 'PC_SENSOR_RANGE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the sensed pressure of the sensor is above 26 psi or '
            'below 2.471 psi.'
        ),
        cmm_page=49,
        reference_name='PC_SENSOR_RANGE_FAIL',
    ),
    FaultBit(
        50, 'PRES_REFRESH_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the pressure value is not refreshed by the pressure '
            'sensor within the valid time frame.'
        ),
        cmm_page=49,
        reference_name='PRES_REFRESH_FAIL',
    ),
    FaultBit(
        51, 'TEMP_REFRESH_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the temperature value is not refreshed by the '
            'temperature sensor within the valid time frame.'
        ),
        cmm_page=49,
        reference_name='TEMP_REFRESH_FAIL',
    ),
    FaultBit(
        52, 'PC_VS_PA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='N',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PC differs from the PA value more than 0.2 psi '
            'absolute. This test is part of the IBIT and the SCBIT only.'
        ),
        cmm_page=49,
        reference_name='PC_VS_PA_FAIL',
    ),
    FaultBit(
        53, 'NOT USED',
        cmm_page=49,
        reference_name='UNUSED',
    ),
    FaultBit(
        54, 'NOT USED',
        cmm_page=49,
        reference_name='UNUSED',
    ),
    FaultBit(
        55, 'NOT USED',
        cmm_page=49,
        reference_name='UNUSED',
    ),
    FaultBit(
        56, 'HSS_OPEN_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the DRIVE_ENABLE_CTR_PNL_OUT line is powered while the '
            'HSS should be open.'
        ),
        cmm_page=50,
        reference_name='HSS_OPEN_FAIL',
    ),
    FaultBit(
        57, 'HSS_SHORT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the DRIVE_ENABLE_CTR_PNL_OUT line is unpowered while the '
            'HSS should be closed.'
        ),
        cmm_page=50,
        reference_name='HSS_SHORT_FAIL',
    ),
    FaultBit(
        58, 'NOT USED',
        cmm_page=50,
        reference_name='UNUSED',
    ),
    FaultBit(
        59, 'OSD_WA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the OSD_CTR_OUT line fails.'
        ),
        cmm_page=50,
        reference_name='OSD_WA_FAIL',
    ),
    FaultBit(
        60, 'AUTO_UNDER_TEST_WA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the AUTO_UNDER_TEST_CTR_CTR_OUT line '
            'fails.'
        ),
        cmm_page=50,
        reference_name='AUTO_UNDER_TEST_WA_FAIL',
    ),
    FaultBit(
        61, 'AUTO_OK_WA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the series discrete output '
            'AUTO_FAIL_CTR_OUT failed.'
        ),
        cmm_page=50,
        reference_name='AUTO_FAIL_CTR_OUT_WA_FAIL',
    ),
    FaultBit(
        62, 'NOT USED',
        cmm_page=50,
        reference_name='UNUSED',
    ),
    FaultBit(
        63, 'BCM_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='no display possible',
        descriptor=(
            'This fail flag will be set if the self test of the BCM fails.'
        ),
        cmm_page=50,
        reference_name='BCM_FAIL',
    ),
    FaultBit(
        64, 'OFV_RAM_REG_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the non destructive test of the OFV microprocessor RAM '
            'fails during CBIT.'
        ),
        cmm_page=51,
        reference_name='OFV_RAM_REG_FAIL',
    ),
    FaultBit(
        65, 'OFV_RAM_EXT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag is set if the non destructive test of the OFV microprocessor external '
            'RAM fails during CBIT.'
        ),
        cmm_page=51,
        reference_name='OFV_RAM_EXT_FAIL',
    ),
    FaultBit(
        66, 'OFV_INI_RAM_REG_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='This fail flag is set if the non destructive test of the OFV',
        descriptor=(
            'microprocessor RAM fails during PUBIT.'
        ),
        cmm_page=51,
        reference_name='OFV_INI_RAM_REG_FAIL',
    ),
    FaultBit(
        67, 'OFV_INI_RAM_EXT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='This fail flag is set if the non destructive test of the OFV',
        descriptor=(
            'microprocessor external RAM fails during PUBIT.'
        ),
        cmm_page=51,
        reference_name='OFV_INI_RAM_EXT_FAIL',
    ),
    FaultBit(
        68, 'OFV_MOT_CUR_LIMIT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the current limitation for the automatic motor fails.'
        ),
        cmm_page=51,
        reference_name='OFV_MOT_CUR_LIMIT_FAIL',
    ),
    FaultBit(
        69, 'OFV_PWR_EXT_AD_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the +15 V DC of the ELACT feed into an A/D converter '
            'input is not in range.'
        ),
        cmm_page=51,
        reference_name='OFV_POW_EXT_AD_FAIL',
    ),
    FaultBit(
        70, 'NOT USED',
        cmm_page=51,
        reference_name='UNUSED',
    ),
    FaultBit(
        71, 'NOT USED',
        cmm_page=51,
        reference_name='UNUSED',
    ),
    FaultBit(
        72, 'OFV_PROM_CRC_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the cyclic redundancy check of the ELACT EPROMS fails.'
        ),
        cmm_page=52,
        reference_name='OFV_PROM_CRC_FAIL',
    ),
    FaultBit(
        73, 'OFV_RS422_WA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the ELACT RS422 interface fails.'
        ),
        cmm_page=52,
        reference_name='OFV_RS422_WA_FAIL',
    ),
    FaultBit(
        74, 'OFV_RS422_CTR_TO_OFV_ACTIVITY_FAIL',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV OR WIRING',
        descriptor=(
            'This fail flag will be set if the ELACT does not detect RS422 activity of the CTR and '
            'the CTR RS422 wraparound is passed.'
        ),
        cmm_page=52,
        reference_name='OFV_RS422_CTR_TO_OFV_ACTIV_FAIL',
    ),
    FaultBit(
        75, 'OFV_RS422_XMIT_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if no ELACT transmitter interrupt activity is detected by '
            'the ELACT.'
        ),
        cmm_page=52,
        reference_name='OFV_RS422_XMIT_FAIL',
    ),
    FaultBit(
        76, 'OFV_DISC_WA_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the discrete input MUX in the ELACT '
            'fails.'
        ),
        cmm_page=52,
        reference_name='OFV_DISC_WA_FAIL',
    ),
    FaultBit(
        77, 'OFV_RVT_EXC_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the ELACT internal discrete wraparound fails.'
        ),
        cmm_page=52,
        reference_name='OFV_RVT_EXC_FAIL',
    ),
    FaultBit(
        78, 'OFV_RVT_POS_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the RVT reference voltage is detected out of range.'
        ),
        cmm_page=52,
        reference_name='OFV_RVT_POS_FAIL',
    ),
    FaultBit(
        79, 'OFV_B737_ID_STATUS',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the internal pin programming is not set to B737 mode.'
        ),
        cmm_page=53,
        reference_name='OFV_B737_ID_FAIL',
    ),
    FaultBit(
        80, 'OFV_AD_TIME_FRAME_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the A/D conversion is not performed within the defined '
            'time frame.'
        ),
        cmm_page=54,
        reference_name='OFV_AD_TIME_FRAME_FAIL',
    ),
    FaultBit(
        81, 'OFV_LOOP_CLOSURE_STATUS',
        auto_fail='0',
        nvm='0',
        recoverable='A',
        fault_indication='No indication, may lead to fault code 007',
        descriptor=(
            'This status fail flag will be set on OFV fault word by the ELACT and evaluated by the '
            'CTR. If the additional conditions are fulfilled the CTR set as result fail flag 007 on '
            'the system fault word.'
        ),
        cmm_page=54,
    ),
    FaultBit(
        82, 'NOT USED',
        cmm_page=54,
        reference_name='UNUSED',
    ),
    FaultBit(
        83, 'OFV_ALU_FAIL',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the arithmetic operation tests of the ALU of the ELACT '
            'fail.'
        ),
        cmm_page=54,
    ),
    FaultBit(
        84, 'NOT USED',
        cmm_page=54,
        reference_name='UNUSED',
    ),
    FaultBit(
        85, 'NOT USED',
        cmm_page=54,
        reference_name='UNUSED',
    ),
    FaultBit(
        86, 'NOT USED',
        cmm_page=54,
        reference_name='UNUSED',
    ),
    FaultBit(
        87, 'OFV_15V_NEG_ADC_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the -15 V DC feed into the A/D converter is out of '
            'range. May be caused by a power supply or A/D converter fail.'
        ),
        cmm_page=54,
        reference_name='OFV_15V_NEG_ADC_FAIL',
    ),
    FaultBit(
        88, 'OFV_HALL_EFF_SEN_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the hall sensor signals are detected in incorrect '
            'combinations.'
        ),
        cmm_page=55,
        reference_name='OFV_HALL_EFFECT_SENSOR_FAIL',
    ),
    FaultBit(
        89, 'NOT USED',
        cmm_page=55,
        reference_name='UNUSED',
    ),
    FaultBit(
        90, 'OFV_CAB_PRESS_SWITCH_STATUS',
        auto_fail='0',
        nvm='1',
        recoverable='A',
        fault_indication='CAB_PRES_SW_ACTIV',
        descriptor=(
            'This status fail flag will be set as long as the cabin pressure switch of the ELACT is '
            'active. Under certain conditions when FC90 is active, the Auto Fail bit can also '
            'change to 1. This behavior can only be noticed when the NVM is downloaded and is not '
            'observable for the flight crew or through the BCM functions. There is no functional '
            'impact and the behavior does not point to a malfunction of the system. No Auto Channel '
            'transfer will occur.'
        ),
        cmm_page=55,
    ),
    FaultBit(
        91, 'OFV_RS422_CTR_TO_OFV_MESSAGE_FAIL',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='CONTRLR LRU FAIL',
        descriptor=(
            'This fail flag will be set if the ELACT receives invalid P messages from the CTR for '
            'longer than 3 seconds.'
        ),
        cmm_page=55,
    ),
    FaultBit(
        92, 'OFV_ELACT_PROG_PIN_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='OFV LRU FAIL',
        descriptor=(
            'This fail flag will be set if the ELACT internal program pin setting shows a forbidden '
            'combination.'
        ),
        cmm_page=55,
        reference_name='OFV_ELACT_PROG_PIN_FAIL',
    ),
    FaultBit(
        93, 'NOT USED',
        cmm_page=55,
        reference_name='UNUSED',
    ),
    FaultBit(
        94, 'NOT USED',
        cmm_page=55,
        reference_name='UNUSED',
    ),
    FaultBit(
        95, 'NOT USED',
        cmm_page=55,
        reference_name='UNUSED',
    ),
    FaultBit(
        96, 'PNL_PROM_CRC_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the cyclic redundancy check of the PNL PROMs fails.'
        ),
        cmm_page=56,
        reference_name='PNL_PROM_CRC_FAIL',
    ),
    FaultBit(
        97, 'NOT USED',
        cmm_page=56,
        reference_name='UNUSED',
    ),
    FaultBit(
        98, 'PNL_NON_DESTRUCTIVE_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the test of the PNL RAM fails.'
        ),
        cmm_page=56,
        reference_name='PNL_NON_DESTRUCTIVE_RAM_FAIL',
    ),
    FaultBit(
        99, 'PNL_ALU_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PNL microcontroller arithmetic operation test fails.'
        ),
        cmm_page=56,
        reference_name='PNL_ALU_FAIL',
    ),
    FaultBit(
        100, 'PNL_ARINC_WA1_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PNL detects a wraparound fail of the ARINC interface '
            'to the master CTR.'
        ),
        cmm_page=56,
        reference_name='PNL_ARINC_WA1_FAIL',
    ),
    FaultBit(
        101, 'PNL_ARINC_WA2_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PNL detects a wraparound fail of the ARINC interface '
            'to the slave CTR.'
        ),
        cmm_page=56,
        reference_name='PNL_ARINC_WA2_FAIL',
    ),
    FaultBit(
        102, 'PNL_A/D_CONVERTER_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PNL A/D converter test fails.'
        ),
        cmm_page=56,
        reference_name='PNL_A/D_CONVERTER_FAIL',
    ),
    FaultBit(
        103, 'PNL_AUTO_FAIL_WA_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the wraparound of the discrete output AUTO_FAIL_PNL_OUT '
            'fails.'
        ),
        cmm_page=57,
        reference_name='PNL_AUTO_FAIL_WA_FAIL',
    ),
    FaultBit(
        104, 'PNL_UNANTICIPATED_PORING_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PNL resets 3 times without detected reason within 6 '
            'minutes.'
        ),
        cmm_page=57,
        reference_name='PNL_UNANTICIPATED_PORING',
    ),
    FaultBit(
        105, 'PNL_WATCHDOG_TIMER_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if the PNL watchdog timer expires.'
        ),
        cmm_page=57,
        reference_name='PNL_WATCHDOG_TIMER_FAIL',
    ),
    FaultBit(
        106, 'PNL_RECEIVED_DISCRETE_INPUT_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag will be set if a discrete input value is out of range.'
        ),
        cmm_page=57,
        reference_name='PNL-RECEIVED_DISCRETE_INPUT_FAIL',
    ),
    FaultBit(
        107, 'PNL_SEVER_VOLTAGE_DROP_HIGH_FAIL',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='SEL PNL LRU FAIL',
        descriptor=(
            'This fail flag is set whenever the CTR state is SB and the OFV state is OP while the '
            'CTRs opmode is not MANUAL and the PNL indicates a high voltage drop from either sever '
            'switch relay.'
        ),
        cmm_page=57,
        reference_name='PNL_SEVER_CLOSED_FAIL',
    ),
    FaultBit(
        108, 'COMM_CTR1_PNL_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='A',
        fault_indication='SYSTEM WIRING; Detail: CPC-PNL WIRING',
        descriptor=(
            'This fail flag will be set by the CTR if the PNL detects no ARINC activity or receives '
            'faulty data from the CTR1 and no wraparound failure of the PNL and the CTR ARINC '
            'interface is detected.'
        ),
        cmm_page=57,
        reference_name='COMM_CTR1_PNL_FAIL',
    ),
    FaultBit(
        109, 'DRIVE_ENABLE_DISAGREE_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='R',
        fault_indication='DRV ENBL ERROR',
        descriptor=(
            'This fail flag will be set if the PNL detects that both DRIVE_ENABLE_CTR_PNL_IN are '
            'operational at the same time or one auto channel is in fail and the '
            'DRIVE_ENABLE_CTR_PNL_IN of this channel is powered at the same time.'
        ),
        cmm_page=58,
        reference_name='DRV_ENBL_DISAGREE_STATUS',
    ),
    FaultBit(
        110, 'COMM_CTR2_PNL_FAIL_FG',
        auto_fail='1',
        nvm='1',
        recoverable='A',
        fault_indication='SYSTEM WIRING; Detail: CPC-PNL WIRING',
        descriptor=(
            'This fail flag will be set by the CTR if the PNL detects no ARINC activity or receives '
            'faulty data from the CTR2 and no wraparound failure of the PNL and the CTR ARINC '
            'interface is detected.'
        ),
        cmm_page=58,
        reference_name='COMM_CTR2_PNL_FAIL',
    ),
    FaultBit(
        111, 'PNL_FAIL_FG',
        auto_fail='0',
        nvm='1',
        recoverable='R',
        fault_indication='No indication',
        descriptor=(
            'This fail flag will be set if a PNL internal fail (fail flags 096 to 106) is detected.'
        ),
        cmm_page=58,
        reference_name='PNL_FAIL',
    ),
]

FAULT_CODE_NAMES = tuple(fault.name for fault in Faults)
STATUS_CODES = frozenset(fault.code for fault in Faults if "STATUS" in fault.name)


def describe_fault_code(code: int) -> str:
    if not 0 <= code < len(Faults):
        return "Not listed in the BIT fault matrix"
    return Faults[code].name


def ConfigureFaultBits():
    """Compatibility entry point for callers from the master branch."""
    return Faults
