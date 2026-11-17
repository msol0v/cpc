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

    def test_reentrant_poll_does_not_start_another_read(self):
        worker = RsWorker()
        calls = []

        def read_pc_alt():
            calls.append(1)
            worker.on_timer_poll()

        worker.read_pc_alt = read_pc_alt
        worker.on_timer_poll()

        self.assertEqual(calls, [1])
        self.assertFalse(worker.is_polling)

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


if __name__ == '__main__':
    unittest.main()
