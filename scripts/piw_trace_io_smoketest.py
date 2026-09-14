"""Pinned verification reads bounded prefixes; appended history is not reloaded."""
import io
import unittest
import piw_native_host as native


class Trace:
    def __init__(self):
        self.stream = io.BytesIO(b'{"type":"first"}\n' + b'x' * 1_000_000)
        self.read_sizes = []

    def read_bytes(self):
        self.read_sizes.append(-1)
        return self.stream.getvalue()

    def open(self, mode):
        owner = self
        class Reader:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size=-1):
                owner.read_sizes.append(size)
                return owner.stream.read(size)
        return Reader()


class TraceIOTests(unittest.TestCase):
    def test_read_stops_at_pin(self):
        trace = Trace()
        prefix = b'{"type":"first"}\n'
        data, rows = native._rows(trace, len(prefix))
        self.assertEqual(data, prefix)
        self.assertEqual(rows, [{'type': 'first'}])
        self.assertEqual(trace.read_sizes, [len(prefix)])

    def test_invalid_prefix_lengths_are_refused(self):
        for value in (-1, True, '10'):
            with self.subTest(value=value), self.assertRaises(native.piw.PIWError):
                native._rows(Trace(), value)


if __name__ == '__main__':
    unittest.main()
