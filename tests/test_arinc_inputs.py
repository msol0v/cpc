import unittest

from PyQt5.QtCore import QCoreApplication

from arinc_handler import ArincWorker, base8_to_int
import uut_encode


class _PortStub:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(bytes(data))


class ArincInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_default_words_have_expected_labels_and_odd_parity(self):
        words = uut_encode.default_uut_in_words()
        self.assertEqual(
            set(words),
            {'203', '204', '206', '220', '344', '346', '107', '127', '271'},
        )
        for label, encoded in words.items():
            word = int(encoded, 16)
            self.assertEqual(word & 0xFF, base8_to_int(label))
            self.assertEqual(word.bit_count() % 2, 1)

    def test_default_bnr_values_decode_back_to_cmm_values(self):
        words = uut_encode.default_uut_in_words()
        expected = {
            '203': (12, 8192.0),
            '204': (12, 7680.0),
            '220': (12, 7682.0),
            '206': (15, 50.0),
            '344': (15, 60.0),
            '346': (15, 21.0),
            '107': (13, 35000.0),
            '127': (13, 2000.0),
        }
        resolutions = {'206': 0.0625, '344': 0.015, '346': 0.015}
        for label, (lsb_bit, value) in expected.items():
            decoded = ArincWorker._decode_bnr(
                int(words[label], 16),
                lsb_bit=lsb_bit,
                resolution=resolutions.get(label, 1.0),
            )
            self.assertAlmostEqual(decoded['value'], value, places=3)
            self.assertEqual(decoded['ssm'], 0b11)

    def test_panel_fault_default_has_auto_selected(self):
        word = int(uut_encode.encode_271(), 16)
        self.assertEqual((word >> 10) & 0xFFFF, 0)
        self.assertEqual((word >> 26) & 1, 1)
        self.assertEqual((word >> 29) & 0x03, 0)

    def test_timers_send_each_required_word_once(self):
        worker = ArincWorker('unused')
        self.assertEqual(worker.timer_50ms.interval(), 50)
        self.assertEqual(worker.timer_63ms.interval(), 63)
        self.assertEqual(worker.timer_100ms.interval(), 100)
        self.assertEqual(worker.timer_200ms.interval(), 200)

        worker.slot_change_uut_word(uut_encode.default_uut_in_words())
        worker.port = _PortStub()
        worker._connected = True

        worker.slot_timer_50ms()
        worker.slot_timer_63ms()
        worker.slot_timer_100ms()
        worker.slot_timer_200ms()

        commands = [data.decode().strip() for data in worker.port.writes]
        sent_words = [command.rsplit(' ', 1)[1] for command in commands]
        sent_labels = {f'{int(word, 16) & 0xFF:02X}' for word in sent_words}
        expected_labels = {
            f'{base8_to_int(label):02X}'
            for label in ('203', '204', '206', '220', '344', '346', '107', '127', '271')
        }
        self.assertEqual(len(commands), 9)
        self.assertTrue(all(command.startswith('send 1 ') for command in commands))
        self.assertEqual(sent_labels, expected_labels)

    def test_selected_port_is_confirmed_only_after_adapter_reply(self):
        worker = ArincWorker('COM77')
        self.assertEqual(worker._port_name, 'COM77')
        worker.port = _PortStub()
        verified = []
        worker.sig_port_verified.connect(verified.append)

        worker._process_line(b'wrong device\n')
        self.assertEqual(verified, [])

        worker._process_line(b'ver.USB-BSCMk0\n')
        self.assertEqual(verified, ['COM77'])
        self.assertTrue(worker._connected)
        self.assertIn(b'start 1\n', worker.port.writes)
        for timer in (worker.timer_50ms, worker.timer_63ms,
                      worker.timer_100ms, worker.timer_200ms):
            timer.stop()


if __name__ == '__main__':
    unittest.main()
