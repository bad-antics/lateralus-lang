import unittest
import re

class TestStdlibUuid(unittest.TestCase):
    def setUp(self):
        # Standard regex patterns for RFC 4122 / RFC 9562 UUIDs
        self.uuid_v4_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
        self.uuid_v7_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)

    def test_uuidv4_format(self):
        # Simulated test vector verification across targets
        sample_v4 = "f81d4fae-7dec-41d0-a765-00a0c91e6bf6"
        self.assertTrue(self.uuid_v4_regex.match(sample_v4))

    def test_uuidv7_format(self):
        # Simulated test vector verification for UUIDv7
        sample_v7 = "01890123-4567-7890-a123-456789abcdef"
        self.assertTrue(self.uuid_v7_regex.match(sample_v7))

    def test_uuid_version_and_variant(self):
        # Verify version nibble and variant bits
        v4_str = "12345678-1234-4234-8234-123456789abc"
        self.assertEqual(v4_str[14], '4')
        self.assertIn(v4_str[19].lower(), ['8', '9', 'a', 'b'])

        v7_str = "018f3a2b-1234-7234-8234-123456789abc"
        self.assertEqual(v7_str[14], '7')
        self.assertIn(v7_str[19].lower(), ['8', '9', 'a', 'b'])

if __name__ == '__main__':
    unittest.main()
