
def __label_encode(label_octal: int) -> str:
    result = 0
    for i in range(0, 8):
        result |= ((label_octal >> i) & 1) << (7 - i)
    return f'{result:02X}'

def __encode_bcd(value: int, digits: int) -> int:
    bcd = 0
    for i in range(digits):
        bcd |= (value % 10) << (i * 4)
        value //= 10
    return bcd

def encode_246(pressure: int) -> str:
    label: str = __label_encode(0o246)
    # Масштабирование: цена деления 0.03125 (множитель 32).
    # По CMM LSB — бит 13, значит сдвиг на 12.
    # SSM 11 = Normal Operation для BNR меток ADIRS.
    val = int(pressure * 32)
    word_payload: int = (0b11 << 29) | (val << 12) | (0b01 << 8)
    return f'{word_payload >> 8:06X}{label}'

def encode_210(airspeed: int) -> str:
    label: str = __label_encode(0o210)
    # Масштабирование: цена деления 0.0625 (множитель 16).
    # По CMM LSB — бит 14, значит сдвиг на 13.
    # SSM 11 = Normal Operation.
    val = int(airspeed * 16)
    word_payload: int = (0b11 << 29) | (val << 13) | (0b01 << 8)
    return f'{word_payload >> 8:06X}{label}'

def encode_351() -> str:
    label: str = __label_encode(0o351)
    word_payload: int = (0b111111 << 10)
    return f'{word_payload >> 8:06X}{label}'

def encode_256(lfe: int) -> str:
    label: str = __label_encode(0o256)
    sign = int(lfe < 0)
    word_payload: int = (0b11 << 29) | (sign << 28) | (lfe << 14) | (0b01 << 8)
    return f'{word_payload >> 8:06X}{label}'
