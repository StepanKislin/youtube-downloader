
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import format_bytes, format_duration, sanitize_filename, is_valid_youtube_url

class TestUtils(unittest.TestCase):
    
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.00 GB")
    
    def test_format_duration(self):
        self.assertEqual(format_duration(0), "00:00")
        self.assertEqual(format_duration(125), "2:05")
        self.assertEqual(format_duration(3665), "1:01:05")
    
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename('test<>file'), 'testfile')
        self.assertEqual(sanitize_filename('test.mp4'), 'test.mp4')
        self.assertEqual(sanitize_filename('a' * 200), 'a' * 100)
    
    def test_is_valid_youtube_url(self):
        self.assertTrue(is_valid_youtube_url('https://youtube.com/watch?v=dQw4w9WgXcQ'))
        self.assertTrue(is_valid_youtube_url('https://youtu.be/dQw4w9WgXcQ'))
        self.assertFalse(is_valid_youtube_url('https://google.com'))

if __name__ == '__main__':
    unittest.main()