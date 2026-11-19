"""Кодирование входных ARINC 429 слов для CPC 7121-19971-01AC."""


def _reverse_label(label_octal: int) -> int:
    if not 0 <= label_octal <= 0xFF:
        raise ValueError('ARINC label must fit in 8 bits')
    result = 0
    for bit in range(8):
        result |= ((label_octal >> bit) & 1) << (7 - bit)
    return result


def _set_odd_parity(word: int) -> int:
    """Установить ARINC bit 32 так, чтобы в 32-битном слове было нечетное число единиц."""
    word &= 0x7FFFFFFF
    if word.bit_count() % 2 == 0:
        word |= 1 << 31
    return word


def _format_word(word: int) -> str:
    return f'{_set_odd_parity(word):08X}'


def encode_bnr(
    label_octal: int,
    value: float,
    *,
    resolution: float,
    lsb_bit: int,
    minimum: float,
    maximum: float,
    sdi: int = 0,
) -> str:
    """Закодировать BNR: magnitude в bits LSB..28, знак в bit 29, SSM=11."""
    if not minimum <= value <= maximum:
        raise ValueError(f'value {value} is outside range {minimum}..{maximum}')
    if not 0 <= sdi <= 3:
        raise ValueError('SDI must be in range 0..3')

    magnitude = round(abs(value) / resolution)
    magnitude_width = 29 - lsb_bit
    if magnitude >= 1 << magnitude_width:
        raise ValueError('value does not fit in the ARINC data field')

    word = _reverse_label(label_octal)
    word |= sdi << 8
    word |= magnitude << (lsb_bit - 1)
    word |= int(value < 0) << 28
    word |= 0b11 << 29  # BNR Normal Operation
    return _format_word(word)


def encode_203(palt_ft: float) -> str:
    return encode_bnr(0o203, palt_ft, resolution=1.0, lsb_bit=12,
                      minimum=-2000, maximum=50000)


def encode_204(cpalt1_ft: float) -> str:
    return encode_bnr(0o204, cpalt1_ft, resolution=1.0, lsb_bit=12,
                      minimum=-2000, maximum=50000)


def encode_220(cpalt2_ft: float) -> str:
    return encode_bnr(0o220, cpalt2_ft, resolution=1.0, lsb_bit=12,
                      minimum=-2000, maximum=50000)


def encode_206(cas_kts: float) -> str:
    return encode_bnr(0o206, cas_kts, resolution=0.0625, lsb_bit=15,
                      minimum=45, maximum=450)


def encode_344(n2_percent: float) -> str:
    return encode_bnr(0o344, n2_percent, resolution=0.015, lsb_bit=15,
                      minimum=0, maximum=123.2)


def encode_346(n1_percent: float) -> str:
    return encode_bnr(0o346, n1_percent, resolution=0.015, lsb_bit=15,
                      minimum=0, maximum=123.2)


def encode_107(scrfl_ft: float) -> str:
    return encode_bnr(0o107, scrfl_ft, resolution=1.0, lsb_bit=13,
                      minimum=-1000, maximum=42000)


def encode_127(slfe_ft: float) -> str:
    return encode_bnr(0o127, slfe_ft, resolution=1.0, lsb_bit=13,
                      minimum=-1000, maximum=14000)


def encode_271(panel_fault_bits: int = 0, auto_selected: bool = True, sdi: int = 0) -> str:
    """Закодировать PNL_FLT; fault bits занимают ARINC bits 11-26."""
    if not 0 <= panel_fault_bits <= 0xFFFF:
        raise ValueError('panel_fault_bits must fit in 16 bits')
    if not 0 <= sdi <= 3:
        raise ValueError('SDI must be in range 0..3')

    word = _reverse_label(0o271)
    word |= sdi << 8
    word |= panel_fault_bits << 10
    word |= int(auto_selected) << 26  # ARINC bit 27: PNL_ARINC_AUTO_FG
    # SSM=00: Normal Operation for a discrete word.
    return _format_word(word)


def default_uut_in_words() -> dict[str, str]:
    """Набор Default Setup из CMM 21-33-20, страницы 1033-1034."""
    return {
        '203': encode_203(8192),
        '204': encode_204(7680),
        '220': encode_220(7682),
        '206': encode_206(50),
        '346': encode_346(21),
        '344': encode_344(60),
        '107': encode_107(35000),
        '127': encode_127(2000),
        '271': encode_271(),
    }
