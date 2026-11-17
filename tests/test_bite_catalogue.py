import unittest

import BITE


class BiteCatalogueTests(unittest.TestCase):
    def test_all_matrix_bits_have_entries_in_bit_order(self):
        self.assertEqual([fault.code for fault in BITE.Faults], list(range(112)))
        self.assertEqual(BITE.Faults[0].name, 'AUTO_CHANNEL_FAIL_FG')
        self.assertEqual(BITE.Faults[16].name, 'PNL_SEVER_OPEN_FAIL_FG')
        self.assertEqual(BITE.Faults[32].name, 'CPC97_FAIL_FG')
        self.assertEqual(BITE.Faults[64].name, 'OFV_RAM_REG_FAIL_FG')
        self.assertEqual(BITE.Faults[96].name, 'PNL_PROM_CRC_FAIL_FG')
        self.assertEqual(BITE.Faults[111].name, 'PNL_FAIL_FG')

    def test_reference_details_are_kept_with_the_bit(self):
        fault = BITE.Faults[32]
        self.assertEqual((fault.auto_fail, fault.nvm, fault.recoverable), ('1', '1', 'R'))
        self.assertIn('CPC97 gate array', fault.descriptor)
        self.assertEqual(fault.cmm_page, 46)

        # The matrix table and Table 5 disagree for this code.
        self.assertEqual(BITE.Faults[17].name, 'NOT USED')
        self.assertIn('Table 5 lists', BITE.Faults[17].descriptor)


if __name__ == '__main__':
    unittest.main()
