import unittest
from io import BytesIO

from PyQt5.QtCore import QCoreApplication
from openpyxl import load_workbook

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

    def test_export_has_separate_decoding_sheets(self):
        raw = bytearray(48)
        raw[10:13] = (4 << 5).to_bytes(3, 'little')
        raw[13:16] = (1 << 23).to_bytes(3, 'little')
        raw[30:32] = (0x8001).to_bytes(2, 'little')
        raw[42:44] = (0x8000).to_bytes(2, 'little')
        book = build_nvm_workbook([f'{byte:02X}' for byte in raw])
        output = BytesIO()
        book.save(output)
        output.seek(0)
        saved = load_workbook(output)
        self.assertEqual(saved.sheetnames,
                         ['Fault buffers', 'DISC_INFO1', 'DISC_INFO2',
                          'Fault words', 'NVM raw'])
        summary = saved['Fault buffers']
        self.assertEqual(summary['I2'].value, '000080')
        self.assertTrue(all(
            cell.alignment.horizontal == 'center' and cell.alignment.vertical == 'center'
            for cell in summary[2]
        ))
        self.assertEqual(summary['I2'].hyperlink.location, "'DISC_INFO1'!A2")
        self.assertEqual(summary['J2'].hyperlink.location, "'DISC_INFO2'!A2")
        self.assertEqual(summary['R2'].hyperlink.location, "'Fault words'!A2")
        self.assertEqual(summary['X2'].hyperlink.location, "'Fault words'!A98")
        self.assertEqual(summary.max_row, 2)
        disc1 = saved['DISC_INFO1']
        self.assertEqual(disc1['F7'].value, 'Flight Mode')
        self.assertEqual(disc1['G7'].value, '4 = CRUISE')
        self.assertEqual(disc1['A2'].alignment.vertical, 'center')
        self.assertEqual(disc1['A2'].alignment.horizontal, 'center')
        self.assertIn('A2:A21', {str(item) for item in disc1.merged_cells.ranges})
        self.assertIn('D2:D21', {str(item) for item in disc1.merged_cells.ranges})
        self.assertEqual(disc1['A2'].border.left.style, 'thin')
        self.assertEqual(disc1['E2'].border.right.style, 'thin')
        self.assertIsNone(disc1['G7'].fill.patternType)
        disc2 = saved['DISC_INFO2']
        self.assertEqual(disc2['F25'].value, 'N2#2 Invalid')
        self.assertEqual(disc2['G25'].value, 'TRUE')
        self.assertIn('B2:B25', {str(item) for item in disc2.merged_cells.ranges})
        words = saved['Fault words']
        self.assertEqual(words['F2'].value, 'AUTO_CHANNEL_FAIL')
        self.assertEqual(words['G2'].value, 'TRUE')
        self.assertEqual(words['F113'].value, 'PNL_FAIL_FG')
        self.assertEqual(words['G113'].value, 'TRUE')
        self.assertIn('C2:C17', {str(item) for item in words.merged_cells.ranges})
        self.assertIn('D98:D113', {str(item) for item in words.merged_cells.ranges})
        self.assertEqual(words.auto_filter.ref, 'A1:G113')
        self.assertEqual(saved['NVM raw']['B12'].value, '80')

    def test_export_has_one_blank_row_between_buffers(self):
        book = build_nvm_workbook(['00'] * 96)
        self.assertIsNone(book['DISC_INFO1']['A22'].value)
        self.assertEqual(book['DISC_INFO1']['A23'].value, 1)
        self.assertIsNone(book['DISC_INFO2']['A26'].value)
        self.assertEqual(book['DISC_INFO2']['A27'].value, 1)
        self.assertIsNone(book['Fault words']['A114'].value)
        self.assertEqual(book['Fault words']['A115'].value, 1)


if __name__ == '__main__':
    unittest.main()
