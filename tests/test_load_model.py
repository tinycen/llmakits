import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llmakits.load_model import parse_model_config


class ParseModelConfigTest(unittest.TestCase):
    def test_combines_direct_and_nested_extra_body_options(self):
        params = parse_model_config(
            {
                "platform": "dashscope_openai",
                "model_name": "example-model",
                "response_format": "json",
                "extra_enable_thinking": "false",
            }
        )

        self.assertEqual(
            {
                "extra_body": {
                    "response_format": {"type": "json_object"},
                    "extra_body": {"enable_thinking": False},
                }
            },
            params,
        )


if __name__ == "__main__":
    unittest.main()
