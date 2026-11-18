import unittest

from FAULT_WORDS import FAULT_NAMES, WORD_START_CODES, decode_fault_word


class FaultWordTests(unittest.TestCase):
    def test_seven_words_cover_table_1018_in_order(self):
        self.assertEqual(list(WORD_START_CODES.values()), [0, 16, 32, 48, 64, 80, 96])
        self.assertEqual(len(FAULT_NAMES), 112)
        self.assertEqual(FAULT_NAMES[32], 'NOT USED')
        self.assertEqual(FAULT_NAMES[111], 'PNL_FAIL_FG')

    def test_bit_order_and_word_boundaries(self):
        for name, start_code in WORD_START_CODES.items():
            decoded = decode_fault_word(name, 0x8001)
            self.assertEqual(decoded[0], ('0', FAULT_NAMES[start_code], 'TRUE'))
            self.assertEqual(decoded[1][2], 'FALSE')
            self.assertEqual(decoded[15], ('15', FAULT_NAMES[start_code + 15], 'TRUE'))


if __name__ == '__main__':
    unittest.main()
