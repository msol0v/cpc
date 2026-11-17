import unittest

from PyQt5.QtCore import QCoreApplication

from RS_handler import RsWorker


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


if __name__ == '__main__':
    unittest.main()
