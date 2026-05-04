import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llmakits.dispatcher import ModelDispatcher
from llmakits.message import builder
from llmakits.utils.retry_handler import RetryHandler
from llmakits.utils.normalize_error import ResponseError


class ImageRetryLoggingTest(unittest.TestCase):
    def test_convert_images_to_base64_succeeds_when_any_image_converts(self):
        def fake_download_encode_base64(url):
            if url.endswith("ok.jpg"):
                return "/9j/valid"
            raise Exception("HTTP Error 404")

        output = io.StringIO()
        with patch.object(builder, "download_encode_base64", fake_download_encode_base64):
            with redirect_stdout(output):
                converted = builder.convert_images_to_base64(
                    ["https://example.com/ok.jpg", "https://example.com/missing.jpg"],
                    image_cache=None,
                )

        stdout = output.getvalue()
        self.assertEqual(1, len(converted))
        self.assertTrue(converted[0].startswith("data:image/jpeg;base64,"))
        self.assertIn("图片下载转base64失败: https://example.com/missing.jpg", stdout)
        self.assertIn("已将图片转换为base64格式: https://example.com/ok.jpg", stdout)
        self.assertIn("图片组base64转换部分成功：成功 1 张，失败 1 张", stdout)

    def test_force_domain_conversion_keeps_successes_when_some_images_fail(self):
        def fake_convert_images_to_base64(img_list, image_cache=None):
            img_url = img_list[0]
            if img_url.endswith("ok.jpg"):
                return [f"data:image/jpeg;base64,{img_url}"]
            raise ResponseError("", "", exception=Exception("HTTP Error 404"), error_tag="图片下载转base64失败")

        handler = RetryHandler("modelscope", "Qwen/Qwen3-VL-235B-A22B-Instruct")
        handler.force_base64_domains.add("example.com")

        with patch("llmakits.utils.retry_handler.convert_images_to_base64", fake_convert_images_to_base64):
            converted = handler._convert_force_domains_to_base64(
                ["https://example.com/ok.jpg", "https://example.com/missing.jpg"]
            )

        self.assertEqual(["data:image/jpeg;base64,https://example.com/ok.jpg"], converted)

    def test_dispatcher_does_not_print_model_header_for_skip_report_image_error(self):
        class FailingModel:
            def send_message(self, messages, message_info):
                response_error = ResponseError(
                    "modelscope",
                    "Qwen/Qwen3-VL-235B-A22B-Instruct",
                    exception=Exception("图片下载转base64失败"),
                    error_tag="图片下载转base64失败",
                )
                response_error.skip_report = True
                raise response_error

        dispatcher = ModelDispatcher()
        llm_models = [
            {
                "sdk_name": "modelscope",
                "model_name": "Qwen/Qwen3-VL-235B-A22B-Instruct",
                "model": FailingModel(),
            }
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(ResponseError):
                dispatcher.execute_task({"user_text": "x", "system_prompt": ""}, llm_models)

        self.assertNotIn(
            "Model modelscope : Qwen/Qwen3-VL-235B-A22B-Instruct",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
