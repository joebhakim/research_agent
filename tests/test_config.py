from __future__ import annotations

from tests import path_setup  # noqa: F401

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_agent.config import load_config


class ConfigTests(unittest.TestCase):
    def test_env_overrides_model_config(self) -> None:
        yaml_text = """
agent:
  mode: native
  thinking:
    extent: medium
    max_react_steps: 8
    beams: 2
    critique_passes: 1
    summarization_ratio: 0.2

search:
  providers: [google_pse]
  topk_per_engine: 8
  freshness_days: 365
  safe_mode: standard
  api_budget_usd: 0.5

storage:
  sqlite_path: "./data/agent.db"
  warc_dir: "./warc"
  runs_dir: "./runs"

models:
  default: local
  local:
    api_base: "http://localhost:8000/v1"
    model_name: "flashresearch-4b-thinking"
    timeout_s: 60
  openrouter:
    api_base: "https://openrouter.ai/api/v1"
    model_name: "alibaba/tongyi-deepresearch-30b-a3b:free"
    timeout_s: 60

routing:
  heavy_uses_openrouter: false
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "agent.yaml"
            config_path.write_text(yaml_text)
            with patch.dict(
                os.environ,
                {
                    "MODEL_API_BASE": "http://example.com/v1",
                    "MODEL_NAME": "stub-model",
                    "MODEL_TIMEOUT_S": "42",
                    "OPENROUTER_API_BASE": "http://openrouter.local/v1",
                    "OPENROUTER_MODEL": "openrouter-stub",
                    "OPENROUTER_TIMEOUT_S": "99",
                },
                clear=False,
            ):
                config = load_config(config_path)

            self.assertEqual(config.models.local.api_base, "http://example.com/v1")
            self.assertEqual(config.models.local.model_name, "stub-model")
            self.assertEqual(config.models.local.timeout_s, 42)
            self.assertEqual(config.models.openrouter.api_base, "http://openrouter.local/v1")
            self.assertEqual(config.models.openrouter.model_name, "openrouter-stub")
            self.assertEqual(config.models.openrouter.timeout_s, 99)


if __name__ == "__main__":
    unittest.main()
