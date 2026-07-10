from __future__ import annotations

import unittest

from rdllm.provider_client import (
    ProviderClientError,
    _extract_openai_compatible_output,
    _normalized_evidence,
)


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

    def test_source_markers_bind_to_supplied_grounding_context(self) -> None:
        mode, verified, source_ids, annotations = _normalized_evidence(
            {"choices": [{"message": {"content": "Answer [S1]"}}]},
            "Answer [S1]",
            {"source_rows": [{"source_id": "S1"}]},
        )
        self.assertEqual(mode, "provider_context_grounded")
        self.assertTrue(verified)
        self.assertEqual(source_ids, ("S1",))
        self.assertEqual(annotations[0]["origin"], "rdllm_context_marker")

    def test_unknown_source_marker_is_not_verified(self) -> None:
        mode, verified, _source_ids, _annotations = _normalized_evidence(
            {},
            "Answer [S99]",
            {"source_rows": [{"source_id": "S1"}]},
        )
        self.assertEqual(mode, "unverified_post_hoc")
        self.assertFalse(verified)


if __name__ == "__main__":
    unittest.main()
