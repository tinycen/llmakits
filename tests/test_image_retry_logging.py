import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from llmakits.dispatcher import ModelDispatcher
from llmakits.message import builder
from llmakits.utils.image_cache import ImageBase64Cache
from llmakits.utils.retry_state import get_retry_state
from llmakits.utils.retry_handler import RetryHandler
from llmakits.utils.normalize_error import ResponseError


class ImageRetryLoggingTest(unittest.TestCase):
    def setUp(self):
        retry_state = get_retry_state()
        retry_state["force_base64_domains"].clear()
        retry_state["domain_failure_stats"].clear()
        retry_state["last_failed_domain"] = ""
        ModelDispatcher.clear_image_cache()

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

    def test_failed_image_url_is_cached_and_skipped(self):
        calls = {"https://example.com/ok.jpg": 0, "https://example.com/missing.jpg": 0}

        def fake_download_encode_base64(url):
            calls[url] += 1
            if url.endswith("ok.jpg"):
                return "/9j/valid"
            raise Exception("HTTP Error 404")

        image_cache = ImageBase64Cache()
        with patch.object(builder, "download_encode_base64", fake_download_encode_base64):
            builder.convert_images_to_base64(
                ["https://example.com/ok.jpg", "https://example.com/missing.jpg"],
                image_cache=image_cache,
            )
            output = io.StringIO()
            with redirect_stdout(output):
                builder.convert_images_to_base64(
                    ["https://example.com/ok.jpg", "https://example.com/missing.jpg"],
                    image_cache=image_cache,
                )

        self.assertEqual(1, calls["https://example.com/ok.jpg"])
        self.assertEqual(1, calls["https://example.com/missing.jpg"])
        self.assertTrue(image_cache.is_failed("https://example.com/missing.jpg"))
        self.assertIn("已从图片组缓存获取可用图片", output.getvalue())

    def test_image_group_cache_reuses_successful_images(self):
        calls = {"https://example.com/ok.jpg": 0, "https://example.com/missing.jpg": 0}

        def fake_download_encode_base64(url):
            calls[url] += 1
            if url.endswith("ok.jpg"):
                return "/9j/valid"
            raise Exception("HTTP Error 404")

        image_cache = ImageBase64Cache()
        img_list = ["https://example.com/ok.jpg", "https://example.com/missing.jpg"]
        with patch.object(builder, "download_encode_base64", fake_download_encode_base64):
            first = builder.convert_images_to_base64(img_list, image_cache=image_cache)
            output = io.StringIO()
            with redirect_stdout(output):
                second = builder.resolve_images_with_cache(img_list, image_cache=image_cache)

        self.assertEqual(first, second)
        self.assertEqual(1, calls["https://example.com/ok.jpg"])
        self.assertEqual(1, calls["https://example.com/missing.jpg"])
        self.assertEqual(1, image_cache.group_size())
        self.assertIn("已从图片组缓存获取可用图片", output.getvalue())

    def test_image_group_cache_all_failed_raises_without_retrying_download(self):
        calls = {"https://example.com/missing.jpg": 0}

        def fake_download_encode_base64(url):
            calls[url] += 1
            raise Exception("HTTP Error 404")

        image_cache = ImageBase64Cache()
        img_list = ["https://example.com/missing.jpg"]
        with patch.object(builder, "download_encode_base64", fake_download_encode_base64):
            with self.assertRaises(ResponseError):
                builder.convert_images_to_base64(img_list, image_cache=image_cache)
            with self.assertRaises(ResponseError):
                builder.resolve_images_with_cache(img_list, image_cache=image_cache)

        self.assertEqual(1, calls["https://example.com/missing.jpg"])
        self.assertEqual(1, image_cache.group_size())

    def test_same_domain_is_recorded_once_per_retry_error(self):
        handler = RetryHandler("modelscope", "Qwen/Qwen3-VL-235B-A22B-Instruct")
        message_config = {
            "include_img": True,
            "img_list": [
                "https://example.com/1.jpg",
                "https://example.com/2.jpg",
                "https://example.com/3.jpg",
            ],
            "system_prompt": "",
            "user_text": "x",
        }

        with patch.object(builder, "download_encode_base64", return_value="/9j/valid"):
            handler.handle_rate_limit_error("download image error", 0, [], message_config)

        stats = handler.domain_failure_stats["example.com"]
        self.assertEqual(1, stats["consecutive"])
        self.assertEqual(1, stats["cumulative"])
        self.assertNotIn("example.com", handler.force_base64_domains)

    def test_retry_image_error_populates_group_cache_for_next_request(self):
        calls = {"https://example.com/ok.jpg": 0, "https://example.com/missing.jpg": 0}

        def fake_download_encode_base64(url):
            calls[url] += 1
            if url.endswith("ok.jpg"):
                return "/9j/valid"
            raise Exception("HTTP Error 404")

        handler = RetryHandler("modelscope", "Qwen/Qwen3-VL-235B-A22B-Instruct")
        img_list = ["https://example.com/ok.jpg", "https://example.com/missing.jpg"]
        message_config = {
            "include_img": True,
            "img_list": img_list,
            "system_prompt": "",
            "user_text": "x",
        }

        with patch.object(builder, "download_encode_base64", fake_download_encode_base64):
            handler.handle_rate_limit_error("download image error", 0, [], message_config)
            output = io.StringIO()
            with redirect_stdout(output):
                resolved_info = handler.preprocess_message_info(
                    {
                        "include_img": True,
                        "img_list": img_list,
                        "system_prompt": "",
                        "user_text": "next",
                    }
                )

        self.assertEqual(1, calls["https://example.com/ok.jpg"])
        self.assertEqual(1, calls["https://example.com/missing.jpg"])
        self.assertEqual(1, len(resolved_info["img_list"]))
        self.assertTrue(resolved_info["img_list"][0].startswith("data:image/jpeg;base64,"))
        self.assertIn("已从图片组缓存获取可用图片", output.getvalue())

    def test_missing_choices_error_is_reported_without_printing_silent_tag(self):
        handler = RetryHandler("modelscope", "moonshotai/Kimi-K2.5")
        response_error = ResponseError(
            "modelscope",
            "moonshotai/Kimi-K2.5",
            exception=IndexError("原始响应中没有choices"),
            error_tag="原始响应中没有choices",
        )

        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(ResponseError):
                handler.handle_exception(response_error, 0, [], {})

        stdout = output.getvalue()
        self.assertTrue(response_error.reported)
        self.assertIn("Model modelscope : moonshotai/Kimi-K2.5", stdout)
        self.assertNotIn("原始响应中没有choices", stdout)
        self.assertNotIn("已提取到报错信息，但未匹配到任何重试场景", stdout)

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

    def test_dispatcher_raises_all_models_failed_after_last_fallback_error(self):
        class FailingModel:
            def __init__(self, error_message):
                self.error_message = error_message

            def send_message(self, messages, message_info):
                raise ResponseError(
                    "vercel",
                    self.error_message,
                    exception=Exception(self.error_message),
                    error_tag="响应异常",
                )

        dispatcher = ModelDispatcher()
        llm_models = [
            {"sdk_name": "vercel", "model_name": "openai/gpt-5-mini", "model": FailingModel("first failed")},
            {"sdk_name": "vercel", "model_name": "google/gemini-3-flash", "model": FailingModel("last failed")},
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(ResponseError) as context:
                dispatcher.execute_task({"user_text": "x", "system_prompt": ""}, llm_models)

        error_message = context.exception.get_error_message()
        self.assertIn("All models failed", error_message)
        self.assertIn("last failed", error_message)

    def test_dispatcher_return_detailed_reports_all_models_failed(self):
        class FailingModel:
            def send_message(self, messages, message_info):
                raise ResponseError(
                    "vercel",
                    "google/gemini-3-flash",
                    exception=Exception("last failed"),
                    error_tag="响应异常",
                )

        dispatcher = ModelDispatcher()
        llm_models = [
            {"sdk_name": "vercel", "model_name": "google/gemini-3-flash", "model": FailingModel()},
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            result = dispatcher.execute_task(
                {"user_text": "x", "system_prompt": ""},
                llm_models,
                return_detailed=True,
            )

        self.assertFalse(result.success)
        self.assertIsInstance(result.error, ResponseError)
        self.assertIn("All models failed", result.error.get_error_message())
        self.assertEqual(0, result.last_tried_index)

    def test_dispatcher_does_not_reprint_model_header_after_next_model_log(self):
        class InvalidModel:
            def send_message(self, messages, message_info):
                return "invalid", 0

        def always_invalid(return_message):
            return False, return_message

        dispatcher = ModelDispatcher()
        llm_models = [
            {"sdk_name": "openrouter", "model_name": "first-model", "model": InvalidModel()},
            {"sdk_name": "modelscope", "model_name": "second-model", "model": InvalidModel()},
        ]

        output = io.StringIO()
        with patch.object(dispatcher.logger, "debug") as debug_log:
            with redirect_stdout(output):
                with self.assertRaises(Exception):
                    dispatcher.execute_task(
                        {"user_text": "x", "system_prompt": ""},
                        llm_models,
                        validate_func=always_invalid,
                    )

        stdout = output.getvalue()
        self.assertIn("1/2 Model openrouter : first-model", stdout)
        self.assertNotIn("2/2 Model modelscope : second-model", stdout)
        self.assertEqual(2, stdout.count("输出结果：条件校验失败, trying next model ..."))
        debug_log.assert_called_once_with("Next model : \n2/2 Model modelscope : second-model")


if __name__ == "__main__":
    unittest.main()
