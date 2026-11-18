import unittest

from PyQt5.QtCore import QCoreApplication

from RS_handler import FaultsBuffer, RsWorker
from main_window import build_nvm_workbook


class FaultBufferAddressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_buffer_read_starts_at_fixed_nvm_address(self):
        worker = RsWorker()
        requests = []

        def read_word(address, priority=50):
            requests.append(('word', address))
            return '0000'

        def read_byte(address, priority=50):
            requests.append(('byte', address))
            return '0E'

        worker.handler.read_word = read_word
        worker.handler.read_byte = read_byte
        worker.read_fbuffs()

        self.assertEqual(requests, [])
        self.assertEqual(worker._fb_current_address, 0x1000)

    def test_ring_covers_only_42_complete_records(self):
        self.assertEqual(RsWorker.next_fault_memory_address(0x1FBE), 0x1000)
        with self.assertRaises(ValueError):
            RsWorker.next_fault_memory_address(0x1FC0)

    def test_fault_byte_timeout_retries_same_address(self):
        worker = RsWorker()
        addresses = []

        def read_byte(address, priority=50):
            addresses.append(address)
            return None if len(addresses) == 1 else '2F'

        worker.handler.read_byte = read_byte
        worker._fb_in_progress = True
        worker._fb_current_address = 0x11D6
        worker._fb_step()

        self.assertEqual(addresses, [0x11D6, 0x11D6])
        self.assertEqual(worker._fb_current_raw, ['2F'])
        self.assertEqual(worker._fb_current_address, 0x11D8)

    def test_read_error_stops_buffer_read(self):
        worker = RsWorker()
        worker.read_fbuffs()
        worker.handler.read_byte = lambda address, priority=50: None
        errors = []
        worker.sig_error.connect(errors.append)

        worker._fb_step()

        self.assertEqual(len(errors), 1)
        self.assertFalse(worker._fb_in_progress)

    def test_unsupported_legacy_constants_are_not_read(self):
        worker = RsWorker()
        requests = []
        worker.handler.read_word = lambda address, priority=50: requests.append(address)
        errors = []
        worker.sig_error.connect(errors.append)

        worker.slot_get_consts()

        self.assertEqual(requests, [])
        self.assertIn('Адреса констант не подтверждены', errors[0])

    def test_nvm_export_uses_physical_addresses(self):
        book = build_nvm_workbook(['FF', '0E', '2F'] + ['00'] * 45)
        sheet = book['NVM raw']

        self.assertEqual(sheet['A2'].value, '1000H')
        self.assertEqual(sheet['B3'].value, '0E')
        self.assertEqual(sheet['A4'].value, '1004H')
        self.assertEqual(sheet['C2'].value, 0)

    def test_shared_byte_fields_and_flight_leg(self):
        raw = ['00', 'AF', '01', '02', '03', '04'] + ['00'] * 42
        buffer = FaultsBuffer(raw)

        self.assertEqual(buffer.intermittent_count, 7)
        self.assertTrue(buffer.bbj_sel_in)
        self.assertEqual(buffer.flight_leg_counter, 0x04030201)

        row = build_nvm_workbook(raw).active
        self.assertEqual(row['E2'].value, 7)
        self.assertEqual(row['F2'].value, 1)
        self.assertEqual(row['G2'].value, 0x04030201)


if __name__ == '__main__':
    unittest.main()
