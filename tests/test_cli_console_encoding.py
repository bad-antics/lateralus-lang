import io
import unittest
from unittest.mock import patch

from lateralus_lang.__main__ import _configure_console_output


class ConsoleEncodingTests(unittest.TestCase):
    def test_cp1252_stream_replaces_unsupported_help_symbols(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
        with patch("sys.stdout", stream), patch("sys.stderr", stream):
            _configure_console_output()
            stream.write("help: λ 🚀")
            stream.flush()
        rendered = raw.getvalue().decode("cp1252")
        self.assertIn("help:", rendered)
        self.assertIn("\\u03bb", rendered)
        self.assertIn("\\U0001f680", rendered)

    def test_utf8_output_remains_unicode(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="utf-8", errors="strict")
        with patch("sys.stdout", stream), patch("sys.stderr", stream):
            _configure_console_output()
            stream.write("help: λ 🚀")
            stream.flush()
        self.assertEqual(raw.getvalue().decode("utf-8"), "help: λ 🚀")


if __name__ == "__main__":
    unittest.main()
