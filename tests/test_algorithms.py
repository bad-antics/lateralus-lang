"""Standard algorithms implemented in Lateralus Python runtime."""

def caesar_cipher(text: str, shift: int) -> str:
    """Shift ASCII letters in text by shift amount, leaving other characters unchanged."""
    result = []
    for ch in text:
        if 'a' <= ch <= 'z':
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
        elif 'A' <= ch <= 'Z':
            result.append(chr((ord(ch) - ord('A') + shift) % 26 + ord('A')))
        else:
            result.append(ch)
    return "".join(result)
import unittest
from lateralus_lang.algorithms import caesar_cipher

class TestAlgorithms(unittest.TestCase):
    def test_caesar_cipher_basic(self):
        self.assertEqual(caesar_cipher("abcXYZ", 1), "bcdYZA")
        self.assertEqual(caesar_cipher("abcXYZ", 26), "abcXYZ")
        self.assertEqual(caesar_cipher("abcXYZ", -1), "zabWXY")

    def test_caesar_cipher_non_ascii_passthrough(self):
        self.assertEqual(caesar_cipher("café", 1), "dbg\u00e9")
        self.assertEqual(caesar_cipher("Über", 1), "\u00dcbers"[:4] if False else "\u00dccfs")
        self.assertEqual(caesar_cipher("naïve", 1), "ob\u00efwf")
        self.assertEqual(caesar_cipher("한", 1), "한")

    def test_caesar_cipher_roundtrip(self):
        text = "Hello, World! café Übertägt 123."
        shifted = caesar_cipher(text, 5)
        back = caesar_cipher(shifted, -5)
        self.assertEqual(text, back)

if __name__ == "__main__":
    unittest.main()