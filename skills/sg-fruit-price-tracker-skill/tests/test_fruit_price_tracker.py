"""Smoke tests for the SG Fruit Price Tracker script.

Pure-stdlib, no network. Covers:
  - Blocklist matching (excluded / not-excluded)
  - Price validation (in-range, out-of-range)
  - Weight parsing (g / kg)
  - aria-label extraction with promo + regular price
  - Dedup by normalized name
  - JSON + CSV output formats
  - Cache TTL behavior
  - Cleanup-old-CSVs retention
  - CLI exit codes (0 / 1 / 2)

Run:
    python3 -m unittest discover -s skills/sg-fruit-price-tracker-skill/tests -v
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
SCRIPT = SCRIPTS / "fruit_price_tracker.py"


def _import_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import fruit_price_tracker  # type: ignore
    return fruit_price_tracker


# --------------------------------------------------------------- blocklist --

class BlocklistTests(unittest.TestCase):
    def test_excludes_yoghurt(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Strawberry Yoghurt Drink 250ml"))

    def test_excludes_juice(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("100% Lychee Juice 1L"))

    def test_excludes_dried(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Dried Strawberries 100g"))

    def test_excludes_cake(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Strawberry Shortcake Slice"))

    def test_excludes_soap(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Peach Body Soap 100g"))

    def test_excludes_wine(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Plum Wine 750ml"))

    def test_allows_fresh_lychee(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("Fresh Lychee 500g"))

    def test_allows_fresh_strawberries(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("Strawberries (USA) 250g"))

    def test_allows_fresh_peach(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("White Peach (Japan) 2pcs"))

    def test_allows_fresh_plum(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("Japanese Plum 500g"))

    def test_blocklist_has_70_plus(self):
        m = _import_module()
        self.assertGreaterEqual(len(m.EXCLUDE_KEYWORDS), 70)


# --------------------------------------------------------------- price ----

class PriceValidationTests(unittest.TestCase):
    def test_valid(self):
        m = _import_module()
        self.assertEqual(m.parse_price("$6.95"), 6.95)
        self.assertEqual(m.parse_price("$  4.20"), 4.20)
        self.assertEqual(m.parse_price("$199.99"), 199.99)

    def test_too_low(self):
        m = _import_module()
        self.assertIsNone(m.parse_price("$0.10"))
        self.assertIsNone(m.parse_price("$0.49"))

    def test_too_high(self):
        m = _import_module()
        self.assertIsNone(m.parse_price("$250.00"))
        self.assertIsNone(m.parse_price("$1000"))

    def test_no_price(self):
        m = _import_module()
        self.assertIsNone(m.parse_price(""))
        self.assertIsNone(m.parse_price("not a price"))


# --------------------------------------------------------------- weight ---

class WeightParsingTests(unittest.TestCase):
    def test_grams(self):
        m = _import_module()
        self.assertEqual(m.parse_weight("Strawberries 250g"), 250)
        self.assertEqual(m.parse_weight("Lychees 500 grams"), 500)

    def test_kilograms(self):
        m = _import_module()
        self.assertEqual(m.parse_weight("Plums 1kg"), 1000)
        self.assertEqual(m.parse_weight("Peaches 2.5 kg"), 2500)

    def test_no_weight(self):
        m = _import_module()
        self.assertIsNone(m.parse_weight("Fresh Lychees (loose)"))


# --------------------------------------------------------------- normalise -

class NormalizeNameTests(unittest.TestCase):
    def test_strips_weight(self):
        m = _import_module()
        self.assertEqual(m.normalize_name("Strawberries 250g"), "strawberries")
        self.assertEqual(m.normalize_name("Lychees 500 g"), "lychees")

    def test_lowercases(self):
        m = _import_module()
        self.assertEqual(m.normalize_name("FRESH PEACHES"), "fresh peaches")

    def test_collapses_whitespace(self):
        m = _import_module()
        self.assertEqual(m.normalize_name("Plums   fresh"), "plums fresh")


# --------------------------------------------------------------- extraction --

SAMPLE_HTML = """
<html><body>
<div class="product-card">
  <a href="/p/str-001" aria-label="Strawberries (USA) 250g">Strawberries</a>
  <div class="price"><span class="was">$8.95</span><span class="now">$6.95</span></div>
  <div class="rating" data-rating="4.3" data-reviews="47">stars</div>
</div>
<div class="product-card">
  <a href="/p/str-002" aria-label="Strawberry Yoghurt Drink 250ml">Yoghurt</a>
  <div class="price"><span class="now">$3.50</span></div>
</div>
<div class="product-card">
  <a href="/p/str-003" aria-label="Dried Strawberries 100g">Dried</a>
  <div class="price"><span class="now">$5.00</span></div>
</div>
<div class="product-card">
  <a href="/p/str-004" aria-label="Strawberries (Korea) 500g">Strawberries</a>
  <div class="price"><span class="now">$11.90</span></div>
</div>
<div class="product-card">
  <a href="/p/str-005" aria-label="Candy">Mystery</a>
  <div class="price"><span class="now">$2.00</span></div>
</div>
<div class="product-card">
  <a href="/p/str-006" aria-label="Premium Strawberries 1kg">Strawberries</a>
  <div class="price"><span class="now">$350.00</span></div>
</div>
</body></html>
""".strip()

DUPLICATE_HTML = """
<html><body>
<div class="product-card">
  <a href="/p/ly-001" aria-label="Fresh Lychees 500g">Lychees</a>
  <div class="price"><span class="now">$12.90</span></div>
</div>
<div class="product-card">
  <a href="/p/ly-002" aria-label="Fresh Lychees 500g">Lychees (dup)</a>
  <div class="price"><span class="now">$13.50</span></div>
</div>
</body></html>
""".strip()


class ParseColdStorageTests(unittest.TestCase):
    def test_extracts_valid_fresh_fruit(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_HTML, "strawberry")
        names = [r["name"] for r in records]
        self.assertIn("Strawberries (USA) 250g", names)
        self.assertIn("Strawberries (Korea) 500g", names)

    def test_excludes_blocked(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_HTML, "strawberry")
        names = [r["name"] for r in records]
        self.assertNotIn("Strawberry Yoghurt Drink 250ml", names)
        self.assertNotIn("Dried Strawberries 100g", names)

    def test_excludes_unrelated_fruit(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_HTML, "strawberry")
        self.assertEqual(len(records), 2)

    def test_excludes_out_of_range_price(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_HTML, "strawberry")
        names = [r["name"] for r in records]
        self.assertNotIn("Premium Strawberries 1kg", names)

    def test_promo_flagged(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_HTML, "strawberry")
        usa = next(r for r in records if "USA" in r["name"])
        self.assertTrue(usa["promo"])
        self.assertEqual(usa["price_sgd"], 6.95)
        self.assertEqual(usa["original_price_sgd"], 8.95)
        self.assertEqual(usa["weight_g"], 250)
        self.assertEqual(usa["rating"], 4.3)
        self.assertEqual(usa["review_count"], 47)

    def test_non_promo(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_HTML, "strawberry")
        kor = next(r for r in records if "Korea" in r["name"])
        self.assertFalse(kor["promo"])
        self.assertIsNone(kor["original_price_sgd"])

    def test_dedup(self):
        m = _import_module()
        records = m.parse_cold_storage(DUPLICATE_HTML, "lychee")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "Fresh Lychees 500g")
        self.assertEqual(records[0]["price_sgd"], 12.90)

    def test_empty_html(self):
        m = _import_module()
        self.assertEqual(m.parse_cold_storage("", "strawberry"), [])
        self.assertEqual(m.parse_cold_storage("<html></html>", "strawberry"), [])


# --------------------------------------------------------------- output ---

class OutputFormatTests(unittest.TestCase):
    def setUp(self):
        m = _import_module()
        self.records = [
            {
                "retailer": "cold_storage",
                "name": "Strawberries (USA) 250g",
                "weight_g": 250,
                "price_sgd": 6.95,
                "original_price_sgd": 8.95,
                "promo": True,
                "rating": 4.3,
                "review_count": 47,
                "url": "https://coldstorage.com.sg/search?q=strawberry",
                "scraped_at": "2026-06-29T09:00:00+08:00",
            }
        ]
        self.m = m

    def test_csv_has_header_and_row(self):
        out = self.m.emit_csv(self.records)
        rdr = csv.DictReader(io.StringIO(out))
        rows = list(rdr)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Strawberries (USA) 250g")
        self.assertEqual(rows[0]["price_sgd"], "6.95")
        self.assertEqual(rows[0]["promo"], "True")

    def test_csv_columns_order(self):
        out = self.m.emit_csv(self.records)
        header_line = out.splitlines()[0]
        self.assertEqual(header_line, ",".join(self.m.CSV_COLUMNS))

    def test_json_serializable(self):
        out = self.m.emit_json(self.records)
        parsed = json.loads(out)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["name"], "Strawberries (USA) 250g")
        self.assertEqual(parsed[0]["price_sgd"], 6.95)


# --------------------------------------------------------------- cache ----

class CacheTests(unittest.TestCase):
    def test_freshness(self):
        m = _import_module()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fake.html"
            p.write_text("hello")
            self.assertTrue(m._cache_is_fresh(p, ttl=60))
            self.assertTrue(m._cache_is_fresh(p, ttl=10**9))
            time.sleep(1.1)
            self.assertFalse(m._cache_is_fresh(p, ttl=0))
            self.assertFalse(m._cache_is_fresh(p, ttl=1))

    def test_cache_key_stable(self):
        m = _import_module()
        k1 = m._cache_key("https://example.com/?q=lychee")
        k2 = m._cache_key("https://example.com/?q=lychee")
        self.assertEqual(k1, k2)
        k3 = m._cache_key("https://example.com/?q=peach")
        self.assertNotEqual(k1, k3)


# --------------------------------------------------------------- cleanup --

class CleanupTests(unittest.TestCase):
    def test_keeps_n_files(self):
        m = _import_module()
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            for i in range(10):
                p = d / f"fruit-prices-2026-06-{i:02d}.csv"
                p.write_text("a,b\n1,2\n")
                time.sleep(0.01)
            deleted = m.cleanup_old_csvs(d, keep=7)
            remaining = sorted(d.glob("fruit-prices-*.csv"))
            self.assertEqual(deleted, 3)
            self.assertEqual(len(remaining), 7)

    def test_no_files(self):
        m = _import_module()
        with tempfile.TemporaryDirectory() as td:
            deleted = m.cleanup_old_csvs(Path(td), keep=7)
            self.assertEqual(deleted, 0)


# --------------------------------------------------------------- CLI -----

class CLITests(unittest.TestCase):
    def _run(self, *args, env=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, timeout=30, env=env,
        )
        return result.returncode, result.stdout, result.stderr

    def test_cli_missing_args(self):
        code, out, err = self._run()
        self.assertNotEqual(code, 0)

    def test_cli_offline_no_cache(self):
        env = {"HOME": "/tmp/sg-fruit-empty-home-xyz"}
        code, out, err = self._run("--all", "--offline", "--json", env=env)
        self.assertEqual(code, 1)
        self.assertIn("all retailers failed", err)


# --------------------------------------------------------------- constants -

class ConstantsTests(unittest.TestCase):
    def test_target_fruits_complete(self):
        m = _import_module()
        for fruit in ("lychee", "peach", "strawberry", "plum"):
            self.assertIn(fruit, m.TARGET_FRUITS)
            self.assertGreater(len(m.TARGET_FRUITS[fruit]), 0)

    def test_constants_in_range(self):
        m = _import_module()
        self.assertEqual(m.MIN_PRICE_SGD, 0.50)
        self.assertEqual(m.MAX_PRICE_SGD, 200.0)
        self.assertLess(m.MIN_PRICE_SGD, m.MAX_PRICE_SGD)

    def test_cache_ttl_one_hour(self):
        m = _import_module()
        self.assertEqual(m.CACHE_TTL_SECONDS, 3600)

    def test_no_subprocess_or_shell_pipes(self):
        src = SCRIPT.read_text()
        self.assertNotIn("subprocess.run", src)
        self.assertNotIn("subprocess.call", src)
        self.assertNotIn("os.system", src)
        self.assertNotIn("os.popen", src)
        self.assertIn("urllib.request", src)
        urlopen_count = src.count("urlopen(")
        self.assertEqual(urlopen_count, 1, "urlopen should only be in the _http_get wrapper")


if __name__ == "__main__":
    unittest.main()
