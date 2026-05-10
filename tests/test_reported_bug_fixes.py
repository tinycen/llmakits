import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llmakits.dispatcher import ModelDispatcher
from llmakits.llm_client import BaseClient, process_stream_response
from llmakits.utils.normalize_error import ResponseError
from llmakits.utils.retry_handler import RetryHandler, should_retry_for_image_error


class ReportedBugFixesTest(unittest.TestCase):
    def test_dispatcher_returns_falsy_validated_value(self):
        class Model:
            def send_message(self, messages, message_info):
                return "raw", 3

        dispatcher = ModelDispatcher()
        result, tokens = dispatcher.execute_task(
            {"user_text": "x", "system_prompt": ""},
            [{"sdk_name": "test", "model_name": "model", "model": Model()}],
            validate_func=lambda value: (True, ""),
        )

        self.assertEqual("", result)
        self.assertEqual(3, tokens)

    def test_dispatcher_success_result_records_model_index(self):
        class Model:
            def send_message(self, messages, message_info):
                return "ok", 1

        dispatcher = ModelDispatcher()
        result = dispatcher.execute_task(
            {"user_text": "x", "system_prompt": ""},
            [{"sdk_name": "test", "model_name": "model", "model": Model()}],
            return_detailed=True,
        )

        self.assertTrue(result.success)
        self.assertEqual(0, result.last_tried_index)

    def test_retry_handler_missing_include_img_defaults_false(self):
        self.assertFalse(should_retry_for_image_error("图片解析失败", {}))

        handler = RetryHandler("test", "model")
        with patch("llmakits.utils.retry_handler.time_wait"):
            should_retry, messages = handler.handle_rate_limit_error("download image error", 0, [], {})

        self.assertTrue(should_retry)
        self.assertEqual([], messages)

    def test_stream_response_skips_empty_chunks(self):
        chunks = [
            SimpleNamespace(choices=[]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="he"))]),
            SimpleNamespace(choices=[SimpleNamespace(delta={"content": "llo"})]),
        ]

        self.assertEqual("hello", process_stream_response(chunks))

    def test_api_key_switch_resets_retry_counter(self):
        class Client(BaseClient):
            def __init__(self):
                super().__init__("test", "model")
                self.remaining_switches = 4

            def _create_chat_completion(self, messages):
                raise Exception("quota exceeded")

            def switch_api_key(self):
                if self.remaining_switches <= 0:
                    return False
                self.remaining_switches -= 1
                return True

        client = Client()

        with patch(
            "llmakits.llm_client.prepare_request_data",
            return_value=([], {"user_text": "x", "include_img": False, "img_list": []}),
        ), patch(
            "llmakits.llm_client.timeout_handler",
            side_effect=Exception("quota exceeded"),
        ), patch(
            "llmakits.utils.retry_handler.ResponseError.extract_error_message",
            return_value="quota exceeded",
        ), patch(
            "llmakits.utils.retry_handler.DEFAULT_RETRY_API_KEYWORDS",
            ["quota exceeded"],
        ):
            with self.assertRaises(ResponseError) as context:
                client.send_message([], {"user_text": "x", "system_prompt": ""})

        self.assertEqual("API_KEY_EXHAUSTED", context.exception.get_error_message())
        self.assertEqual(0, client.remaining_switches)


if __name__ == "__main__":
    unittest.main()
