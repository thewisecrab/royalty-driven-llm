from __future__ import annotations

import unittest

from rdllm.provider_client import ProviderClientError, _extract_openai_compatible_output


class ProviderClientTests(unittest.TestCase):
    def test_extracts_openai_compatible_chat_content(self) -> None:
        output, finish_reason = _extract_openai_compatible_output(
            {
                "choices": [
                    {
                        "message": {"content": "grounded provider output"},
                        "finish_reason": "stop",
                    }
                ]
            }
        )
        self.assertEqual(output, "grounded provider output")
        self.assertEqual(finish_reason, "stop")

    def test_content_filter_blocks_attribution(self) -> None:
        with self.assertRaises(ProviderClientError):
            _extract_openai_compatible_output(
                {
                    "choices": [
                        {
                            "message": {"content": "filtered"},
                            "finish_reason": "content_filter",
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
