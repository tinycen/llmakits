import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llmakits.message.formatter import convert_to_json


class ConvertToJsonTest(unittest.TestCase):
    def test_accepts_python_literal_without_executing_code(self):
        self.assertEqual({"name": "llmakits"}, convert_to_json("{'name': 'llmakits'}"))

    def test_rejects_executable_expression(self):
        with self.assertRaisesRegex(Exception, "format_json_error"):
            convert_to_json("__import__('os').system('echo unsafe')")


if __name__ == "__main__":
    unittest.main()
