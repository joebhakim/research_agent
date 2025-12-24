from __future__ import annotations

from tests import path_setup  # noqa: F401

import unittest

from research_agent.search.providers import google_pse


class GooglePSEUtilsTests(unittest.TestCase):
    def test_apply_site_filters(self) -> None:
        self.assertEqual(
            google_pse._apply_site_filters("query", ["example.com"]),
            "query site:example.com",
        )
        self.assertEqual(
            google_pse._apply_site_filters("query", ["a.com", "b.com"]),
            "query (site:a.com OR site:b.com)",
        )

    def test_map_safe_mode(self) -> None:
        self.assertEqual(google_pse._map_safe_mode("strict"), "active")
        self.assertEqual(google_pse._map_safe_mode("off"), "off")

    def test_clamp(self) -> None:
        self.assertEqual(google_pse._clamp(0, 1, 10), 1)
        self.assertEqual(google_pse._clamp(5, 1, 10), 5)
        self.assertEqual(google_pse._clamp(11, 1, 10), 10)


if __name__ == "__main__":
    unittest.main()
