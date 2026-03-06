#!/usr/bin/env python3
"""
Standalone unit tests for geocoding lang parameter support.
No Django project setup needed — all HTTP calls are mocked.

Usage:
    cd /home/alex/projects/voyage/backend/server
    python3 test_geocoding_lang.py
"""

import sys
import json
import unittest
from unittest.mock import patch, MagicMock
import types

# ---------------------------------------------------------------------------
# Minimal stubs so geocoding.py can be imported without a full Django project
# ---------------------------------------------------------------------------
django_module = types.ModuleType("django")
django_conf_module = types.ModuleType("django.conf")


class _Settings:
    GOOGLE_MAPS_API_KEY = None


settings = _Settings()
django_conf_module.settings = settings
django_module.conf = django_conf_module
sys.modules.setdefault("django", django_module)
sys.modules.setdefault("django.conf", django_conf_module)

# Stub worldtravel models (not used by the functions under test)
for mod_name in ("worldtravel", "worldtravel.models"):
    m = types.ModuleType(mod_name)
    for attr in ("Region", "City", "VisitedRegion", "VisitedCity"):
        setattr(m, attr, None)
    sys.modules.setdefault(mod_name, m)

sys.path.insert(0, "/home/alex/projects/voyage/backend/server")
from adventures.geocoding import search_osm, search_google  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mock_response(json_data, status_code=200):
    r = MagicMock()
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    r.status_code = status_code
    return r


_OSM_RESULT = [
    {
        "lat": "50.0755",
        "lon": "14.4378",
        "name": "Prague",
        "display_name": "Prague, Czech Republic",
        "type": "city",
        "category": "place",
        "importance": 0.9,
        "addresstype": "city",
    }
]

_GOOGLE_RESULT = {
    "places": [
        {
            "displayName": {"text": "Prague"},
            "formattedAddress": "Prague, Czech Republic",
            "location": {"latitude": 50.0755, "longitude": 14.4378},
            "types": ["locality"],
            "rating": 4.5,
            "userRatingCount": 1000,
        }
    ]
}


# ---------------------------------------------------------------------------
# Tests: search_osm (Nominatim)
# ---------------------------------------------------------------------------
class TestSearchOsmLang(unittest.TestCase):
    def test_explicit_lang_en(self):
        """search_osm('Prague', lang='en') sends Accept-Language: en"""
        with patch(
            "requests.get", return_value=_mock_response(_OSM_RESULT)
        ) as mock_get:
            search_osm("Prague", lang="en")
            headers = mock_get.call_args[1].get("headers", {})
            self.assertEqual(headers.get("Accept-Language"), "en")

    def test_explicit_lang_de(self):
        """search_osm('Prague', lang='de') sends Accept-Language: de"""
        with patch("requests.get", return_value=_mock_response([])) as mock_get:
            search_osm("Prague", lang="de")
            headers = mock_get.call_args[1].get("headers", {})
            self.assertEqual(headers.get("Accept-Language"), "de")

    def test_default_lang_is_en(self):
        """search_osm('Prague') without lang defaults to Accept-Language: en"""
        with patch("requests.get", return_value=_mock_response([])) as mock_get:
            search_osm("Prague")
            headers = mock_get.call_args[1].get("headers", {})
            self.assertEqual(
                headers.get("Accept-Language"),
                "en",
                f"Expected 'en', got {headers.get('Accept-Language')!r}",
            )

    def test_returns_list(self):
        """search_osm returns a list"""
        with patch("requests.get", return_value=_mock_response(_OSM_RESULT)):
            result = search_osm("Prague", lang="en")
            self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# Tests: search_google (Google Places)
# ---------------------------------------------------------------------------
class TestSearchGoogleLang(unittest.TestCase):
    def setUp(self):
        settings.GOOGLE_MAPS_API_KEY = "test-api-key"

    def tearDown(self):
        settings.GOOGLE_MAPS_API_KEY = None

    def test_explicit_lang_en(self):
        """search_google('Prague', lang='en') posts languageCode: 'en'"""
        with patch(
            "requests.post", return_value=_mock_response(_GOOGLE_RESULT)
        ) as mock_post:
            search_google("Prague", lang="en")
            payload = mock_post.call_args[1].get("json", {})
            self.assertIn("languageCode", payload)
            self.assertEqual(payload["languageCode"], "en")

    def test_explicit_lang_fr(self):
        """search_google('Prague', lang='fr') posts languageCode: 'fr'"""
        with patch(
            "requests.post", return_value=_mock_response(_GOOGLE_RESULT)
        ) as mock_post:
            search_google("Prague", lang="fr")
            payload = mock_post.call_args[1].get("json", {})
            self.assertEqual(payload.get("languageCode"), "fr")

    def test_default_lang_is_en(self):
        """search_google('Prague') without lang defaults to languageCode: 'en'"""
        with patch(
            "requests.post", return_value=_mock_response(_GOOGLE_RESULT)
        ) as mock_post:
            search_google("Prague")
            payload = mock_post.call_args[1].get("json", {})
            self.assertEqual(
                payload.get("languageCode"),
                "en",
                f"Expected 'en', got {payload.get('languageCode')!r}",
            )

    def test_returns_list(self):
        """search_google returns a list"""
        with patch("requests.post", return_value=_mock_response(_GOOGLE_RESULT)):
            result = search_google("Prague", lang="en")
            self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Geocoding lang parameter — unit tests")
    print("=" * 60)
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromNames(
        ["__main__.TestSearchOsmLang", "__main__.TestSearchGoogleLang"]
    )
    result = runner.run(suite)
    print("=" * 60)
    if result.wasSuccessful():
        print(f"ALL {result.testsRun} TESTS PASSED ✓")
        sys.exit(0)
    else:
        print(f"FAILURES: {len(result.failures)}, ERRORS: {len(result.errors)}")
        sys.exit(1)
