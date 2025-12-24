from __future__ import annotations

from tests import path_setup  # noqa: F401

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from research_agent.config import (
    AgentConfig,
    AppConfig,
    ModelEndpointConfig,
    ModelsConfig,
    RoutingConfig,
    SearchConfig,
    StorageConfig,
    ThinkingConfig,
)
from research_agent.llm.router import RoutedModel
from research_agent.runner import run
from research_agent.search.broker import SearchBroker
from research_agent.types import SearchResult
from tests.stubs import StubLLM, stub_fetch_url_factory


class PipelineTests(unittest.TestCase):
    def test_pipeline_water_boiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            config = AppConfig(
                agent=AgentConfig(
                    mode="native",
                    thinking=ThinkingConfig(
                        extent="medium",
                        max_react_steps=8,
                        beams=2,
                        critique_passes=1,
                        summarization_ratio=0.2,
                    ),
                ),
                search=SearchConfig(
                    providers=["google_pse"],
                    topk_per_engine=8,
                    freshness_days=365,
                    safe_mode="standard",
                    api_budget_usd=0.0,
                ),
                storage=StorageConfig(
                    sqlite_path=base / "agent.db",
                    warc_dir=base / "warc",
                    runs_dir=base / "runs",
                ),
                models=ModelsConfig(
                    default="local",
                    local=ModelEndpointConfig(
                        api_base="http://localhost:8000/v1",
                        model_name="stub",
                        timeout_s=60,
                    ),
                    openrouter=ModelEndpointConfig(
                        api_base="http://openrouter.local/v1",
                        model_name="stub-openrouter",
                        timeout_s=60,
                    ),
                ),
                routing=RoutingConfig(heavy_uses_openrouter=False),
            )

            urls = [
                "fixture://water_boiling_1",
                "fixture://water_boiling_2",
            ]
            results = []
            now = datetime.utcnow()
            for idx, url in enumerate(urls, start=1):
                results.append(
                    SearchResult(
                        engine="google_pse",
                        title=f"Fixture {idx}",
                        url=url,
                        snippet="fixture snippet",
                        rank=idx,
                        retrieved_at=now,
                    )
                )

            fixtures_dir = Path(__file__).resolve().parent / "fixtures"
            url_map = {
                "fixture://water_boiling_1": "water_boiling_1.html",
                "fixture://water_boiling_2": "water_boiling_2.html",
            }
            fetch_stub = stub_fetch_url_factory(fixtures_dir, url_map)

            with patch.object(SearchBroker, "search", return_value=results):
                with patch("research_agent.runner.fetch_url", side_effect=fetch_stub):
                    with patch(
                        "research_agent.runner.get_model_client",
                        return_value=RoutedModel(name="local", client=StubLLM()),
                    ):
                        output = run("water boils at what temperature", config)

            report_text = output.report_path.read_text()
            self.assertIn("water boils", report_text.lower())
            self.assertTrue((output.report_path.parent / "provenance.json").exists())


if __name__ == "__main__":
    unittest.main()
