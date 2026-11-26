"""Колонки и формат строки журнала ошибок"""

from RS_handler import RsWorker, FaultsBuffer
from FAULT_WORDS import FAULT_NAMES


FAULT_BUFFER_HEADERS = (
    'Buffer', 'Address', 'Fault Code of failure caused the entry', 'Fault Flag Name',
    'Intermittent counter', 'BBJ_SEL_IN setting of DISC_INFO3',
    'Flight leg counter', 'Elapsed time counters (s)',
    'DISC_INFO1', 'DISC_INFO2', 'Ambient pressure (hPa)',
    'Cabin pressure (hPa)', 'Ambient pressure rate (SLFpm)',
    'Cabin pressure rate (SLFpm)', 'Cruise flight level (FL)',
    'Landing field elevation (ft)', 'OFV position (deg)',
    'DCPCS_FAULT_WORD', 'EXT_SYS_FAULT_WORD', 'CTR_FAULT_WORD1',
    'CTR_FAULT_WORD2', 'OFV_FAULT_WORD1', 'OFV_FAULT_WORD2',
    'PNL_FAULT_WORD1', 'PREF (hPa)', 'OFV Command BR (deg)',
)


def fault_buffer_row(index, buffer):
    return (
        index,
        f'{RsWorker.FAULT_MEMORY_START + index * FaultsBuffer.SIZE * 2:04X}H',
        buffer.fault_code,
        FAULT_NAMES[buffer.fault_code] if 0 <= buffer.fault_code < len(FAULT_NAMES) else 'Not listed in BIT fault matrix',
        buffer.intermittent_count,
        int(buffer.bbj_sel_in),
        buffer.flight_leg_counter,
        buffer.elapsed_time_seconds,
        f'{buffer.disc_info1:06X}',
        f'{buffer.disc_info2:06X}',
        buffer.ambient_pressure_hpa,
        buffer.cabin_pressure_hpa,
        buffer.ambient_pressure_rate_slfpm,
        buffer.cabin_pressure_rate_slfpm,
        buffer.cruise_flight_level,
        buffer.landing_field_elevation_ft,
        buffer.ofv_position_deg,
        f'{buffer.dcpcs_fault_word:04X}',
        f'{buffer.ext_sys_fault_word:04X}',
        f'{buffer.ctr_fault_word1:04X}',
        f'{buffer.ctr_fault_word2:04X}',
        f'{buffer.ofv_fault_word1:04X}',
        f'{buffer.ofv_fault_word2:04X}',
        f'{buffer.pnl_fault_word1:04X}',
        buffer.pref_hpa,
        buffer.ofv_command_br_deg,
    )
