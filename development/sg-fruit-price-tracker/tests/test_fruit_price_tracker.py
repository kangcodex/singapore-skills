"""Smoke tests for the SG Fruit Price Tracker script.

Pure-stdlib, no network. Covers:
  - Blocklist matching (excluded / not-excluded)
  - Price validation (in-range, out-of-range)
  - Weight parsing (g / kg)
  - Cold Storage aria-label extraction with promo + regular price
  - FairPrice data-testid extraction
  - Dedup by normalized name
  - JSON + CSV output formats
  - Cache TTL behavior
  - Cleanup-old-CSVs retention
  - CLI exit codes (0 / 1 / 2)
  - All 30 target fruits present

Run:
    python3 -m unittest discover -s development/sg-fruit-price-tracker/tests -v
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
SCRIPTS = HERE.parents[2] / "skills" / "sg-fruit-price-tracker-skill" / "scripts"
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

    def test_excludes_apple_cider_vinegar(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Apple Cider Vinegar 500ml"))

    def test_excludes_grape_capsule(self):
        m = _import_module()
        self.assertTrue(m.is_blocked("Grape Seed Extract Capsules 60s"))

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

    def test_allows_durian(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("Musang King Durian 1kg"))

    def test_allows_dragon_fruit(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("Red Dragon Fruit 1pc"))

    def test_allows_mangosteen(self):
        m = _import_module()
        self.assertFalse(m.is_blocked("Fresh Mangosteen 500g"))

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


# --------------------------------------------------------------- cold_storage --

SAMPLE_CS_HTML = """
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
        records = m.parse_cold_storage(SAMPLE_CS_HTML, ["strawberry"])
        names = [r["name"] for r in records]
        self.assertIn("Strawberries (USA) 250g", names)
        self.assertIn("Strawberries (Korea) 500g", names)

    def test_excludes_blocked(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_CS_HTML, ["strawberry"])
        names = [r["name"] for r in records]
        self.assertNotIn("Strawberry Yoghurt Drink 250ml", names)
        self.assertNotIn("Dried Strawberries 100g", names)

    def test_excludes_unrelated_fruit(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_CS_HTML, ["strawberry"])
        self.assertEqual(len(records), 2)

    def test_excludes_out_of_range_price(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_CS_HTML, ["strawberry"])
        names = [r["name"] for r in records]
        self.assertNotIn("Premium Strawberries 1kg", names)

    def test_promo_flagged(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_CS_HTML, ["strawberry"])
        usa = next(r for r in records if "USA" in r["name"])
        self.assertTrue(usa["promo"])
        self.assertEqual(usa["price_sgd"], 6.95)
        self.assertEqual(usa["original_price_sgd"], 8.95)
        self.assertEqual(usa["weight_g"], 250)
        self.assertEqual(usa["rating"], 4.3)
        self.assertEqual(usa["review_count"], 47)
        self.assertEqual(usa["retailer"], "cold_storage")

    def test_non_promo(self):
        m = _import_module()
        records = m.parse_cold_storage(SAMPLE_CS_HTML, ["strawberry"])
        kor = next(r for r in records if "Korea" in r["name"])
        self.assertFalse(kor["promo"])
        self.assertIsNone(kor["original_price_sgd"])

    def test_dedup(self):
        m = _import_module()
        records = m.parse_cold_storage(DUPLICATE_HTML, ["lychee"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "Fresh Lychees 500g")
        self.assertEqual(records[0]["price_sgd"], 12.90)

    def test_empty_html(self):
        m = _import_module()
        self.assertEqual(m.parse_cold_storage("", ["strawberry"]), [])
        self.assertEqual(m.parse_cold_storage("<html></html>", ["strawberry"]), [])

    def test_multi_fruit_keys(self):
        """Should match if ANY of the fruit keys hit (e.g., ['peach', 'plum'])."""
        m = _import_module()
        html = '<a href="/x" aria-label="White Peach 2pcs">x</a><span class="now">$5.00</span>'
        records = m.parse_cold_storage(html, ["peach", "plum"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["name"], "White Peach 2pcs")

    def test_dragon_fruit_and_pitaya_aliases_are_extracted(self) -> None:
        # Given
        m = _import_module()
        html = ('<a aria-label="Dragon Fruit 400g">x</a><span class="now">$3.20</span>'
                '<a aria-label="Red Pitaya 500g">x</a><span class="now">$5.90</span>')
        # When
        records = m.parse_cold_storage(html, ["dragon_fruit"])
        # Then
        self.assertEqual({record["name"] for record in records}, {"Dragon Fruit 400g", "Red Pitaya 500g"})


# --------------------------------------------------------------- fairprice --

SAMPLE_FP_HTML = """
<html><body>
<a href="/product/agroberries-premium-blueberry-bleuets-125g-10632060" class="p">
  <div data-testid="product-name-and-metadata" class="m">
    <span data-testid="highlighted-promo-label"></span>
    <span weight="normal" color="#333333" class="n">Fresh Blueberries</span>
  </div>
  <div class="w">
    <span color="#666666" class="w">125g</span>
  </div>
</a>
<div class="price">
  <span weight="black" class="p">$3.95</span>
</div>
<div data-testid="ratings-star-container" class="r">
  <span aria-label="Average rating is 4.0" class="r">4.0</span>
</div>

<a href="/product/donut-peach-500g-13024402" class="p">
  <div data-testid="product-name-and-metadata" class="m">
    <span weight="normal" color="#333333" class="n">Spain Donut Peach</span>
  </div>
  <div class="w">
    <span color="#666666" class="w">500g</span>
  </div>
</a>
<div class="price">
  <span weight="black" class="p">$11.20</span>
  <span aria-label="Original price"><span class="old">$13.50</span></span>
</div>

<a href="/product/apple-juice-1l" class="p">
  <div data-testid="product-name-and-metadata" class="m">
    <span weight="normal" color="#333333" class="n">Apple Juice 1L</span>
  </div>
</a>
<div class="price">
  <span weight="black" class="p">$5.50</span>
</div>

<a href="/product/china-fuji-apples-5-per-pack" class="p">
  <div data-testid="product-name-and-metadata" class="m">
    <span weight="normal" color="#333333" class="n">China Fuji Apples</span>
  </div>
  <div class="w">
    <span color="#666666" class="w">5 per pack</span>
  </div>
</a>
<div class="price">
  <span weight="black" class="p">$4.50</span>
</div>

<a href="/product/cheap-strawberry-001" class="p">
  <div data-testid="product-name-and-metadata" class="m">
    <span weight="normal" color="#333333" class="n">Bulk Strawberries 5kg</span>
  </div>
</a>
<div class="price">
  <span weight="black" class="p">$250.00</span>
</div>
</body></html>
""".strip()


class ParseFairPriceTests(unittest.TestCase):
    def test_extracts_fresh_fruit(self):
        m = _import_module()
        records = m.parse_fairprice(SAMPLE_FP_HTML, ["blueberry"])
        names = [r["name"] for r in records]
        self.assertIn("Fresh Blueberries", names)
        self.assertEqual(records[0]["retailer"], "fairprice")
        self.assertEqual(records[0]["price_sgd"], 3.95)
        self.assertEqual(records[0]["weight_g"], 125)
        self.assertEqual(records[0]["rating"], 4.0)
        self.assertIsNone(records[0]["review_count"])  # FP doesn't expose this

    def test_excludes_juice(self):
        m = _import_module()
        records = m.parse_fairprice(SAMPLE_FP_HTML, ["apple"])
        names = [r["name"] for r in records]
        self.assertNotIn("Apple Juice 1L", names)
        self.assertIn("China Fuji Apples", names)

    def test_excludes_out_of_range_price(self):
        m = _import_module()
        records = m.parse_fairprice(SAMPLE_FP_HTML, ["strawberry"])
        self.assertEqual(records, [])

    def test_promo_flagged(self):
        m = _import_module()
        records = m.parse_fairprice(SAMPLE_FP_HTML, ["peach"])
        peach = next(r for r in records if "Donut" in r["name"])
        self.assertTrue(peach["promo"])
        self.assertEqual(peach["price_sgd"], 11.20)
        self.assertEqual(peach["original_price_sgd"], 13.50)
        self.assertEqual(peach["weight_g"], 500)

    def test_url_format(self):
        m = _import_module()
        records = m.parse_fairprice(SAMPLE_FP_HTML, ["blueberry"])
        self.assertTrue(records[0]["url"].startswith("https://www.fairprice.com.sg/product/"))
        self.assertIn("10632060", records[0]["url"])

    def test_empty_html(self):
        m = _import_module()
        self.assertEqual(m.parse_fairprice("", ["apple"]), [])
        self.assertEqual(m.parse_fairprice("<html></html>", ["apple"]), [])

    def test_unrendered_html(self):
        """If FairPrice switches to client-side rendering, the page has no
        data-testid markers. Parser must return [] (not crash)."""
        m = _import_module()
        self.assertEqual(
            m.parse_fairprice("<html><body>nothing here</body></html>", ["apple"]),
            [],
        )


# --------------------------------------------------------------- sheng_siong --

class ShengSiongTests(unittest.TestCase):
    def test_always_unavailable(self):
        m = _import_module()
        records = m.scrape_sheng_siong()
        self.assertEqual(records, [])

    def test_wrapper_unavailable_message(self):
        m = _import_module()
        retailer, payload = m.scrape_sheng_siong_wrapper(["apple"])
        self.assertEqual(retailer, "sheng_siong")
        self.assertIsInstance(payload, str)
        self.assertIn("meteor_spa", payload)


# --------------------------------------------------------------- fruit list --

class FruitListTests(unittest.TestCase):
    def test_30_fruits(self):
        m = _import_module()
        self.assertEqual(len(m.TARGET_FRUITS), 30)

    def test_legacy_fruits_present(self):
        m = _import_module()
        for fruit in ("lychee", "peach", "strawberry", "plum"):
            self.assertIn(fruit, m.TARGET_FRUITS)

    def test_exotic_fruits_present(self):
        m = _import_module()
        for fruit in ("durian", "dragon_fruit", "rambutan", "mangosteen", "jackfruit", "pomelo"):
            self.assertIn(fruit, m.TARGET_FRUITS)

    def test_common_fruits_present(self):
        m = _import_module()
        for fruit in ("apple", "banana", "orange", "mango", "watermelon", "pineapple"):
            self.assertIn(fruit, m.TARGET_FRUITS)

    def test_each_fruit_has_keywords(self):
        m = _import_module()
        for fruit, kws in m.TARGET_FRUITS.items():
            self.assertGreater(len(kws), 0, f"{fruit} has no keywords")
            for kw in kws:
                self.assertGreater(len(kw), 0, f"{fruit} has empty keyword")


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
            },
            {
                "retailer": "fairprice",
                "name": "Fresh Blueberries",
                "weight_g": 125,
                "price_sgd": 3.95,
                "original_price_sgd": None,
                "promo": False,
                "rating": 4.0,
                "review_count": None,
                "url": "https://www.fairprice.com.sg/product/abc-123",
                "scraped_at": "2026-06-29T09:00:00+08:00",
            },
        ]
        self.m = m

    def test_csv_has_header_and_rows(self):
        out = self.m.emit_csv(self.records)
        rdr = csv.DictReader(io.StringIO(out))
        rows = list(rdr)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["retailer"], "cold_storage")
        self.assertEqual(rows[1]["retailer"], "fairprice")

    def test_csv_columns_order(self):
        out = self.m.emit_csv(self.records)
        header_line = out.splitlines()[0]
        self.assertEqual(header_line, ",".join(self.m.CSV_COLUMNS))

    def test_json_serializable(self):
        out = self.m.emit_json(self.records)
        parsed = json.loads(out)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "Strawberries (USA) 250g")
        self.assertEqual(parsed[1]["retailer"], "fairprice")


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

    def test_offline_cli_reads_seeded_caches_without_touching_user_home(self) -> None:
        # Given
        m = _import_module()
        cases = (("cold_storage", "strawberry", m.COLDSTORAGE_SEARCH.format(q="strawberry"), SAMPLE_CS_HTML, 2),
                 ("fairprice", "blueberry", m.FAIRPRICE_FRUITS_CATEGORY, SAMPLE_FP_HTML, 1))
        for retailer, fruit, url, html, count in cases:
            with self.subTest(retailer=retailer), tempfile.TemporaryDirectory() as home:
                cache = Path(home) / ".hermes" / "cache" / "sg-fruit-prices"
                cache.mkdir(parents=True)
                (cache / f"{m._cache_key(url)}.html").write_text(html, encoding="utf-8")
                # When
                code, out, err = self._run("--fruit", fruit, "--retailer", retailer,
                                           "--offline", "--json", env={"HOME": home})
                # Then
                self.assertEqual(code, 0, err)
                records = json.loads(out)
                self.assertEqual(len(records), count)
                self.assertTrue(all(record["retailer"] == retailer and record["name"] and record["price_sgd"] > 0 for record in records))

    def test_cli_offline_no_cache(self):
        env = {"HOME": "/tmp/sg-fruit-empty-home-xyz"}
        code, out, err = self._run("--all", "--offline", "--json", env=env)
        self.assertEqual(code, 1)
        self.assertIn("all retailers failed", err)

    def test_cli_fruit_choices(self):
        """All 30 fruits should be valid --fruit choices."""
        m = _import_module()
        # Just verify the parser accepts one of the new fruits
        for fruit in ("apple", "mango", "durian", "dragon_fruit"):
            with tempfile.TemporaryDirectory() as home:
                env = {"HOME": home}
                code, out, err = self._run("--fruit", fruit, "--offline", "--json", env=env)
                # No cache -> all fail, but exit code 1 (not argparse error)
                self.assertEqual(code, 1)

    def test_cli_retailer_choices(self):
        m = _import_module()
        for retailer in ("cold_storage", "fairprice", "sheng_siong"):
            with tempfile.TemporaryDirectory() as home:
                env = {"HOME": home}
                code, out, err = self._run(
                    "--fruit", "apple", "--retailer", retailer,
                    "--offline", "--json", env=env,
                )
                self.assertIn(code, (0, 1, 2))
                if retailer == "sheng_siong":
                    self.assertEqual(code, 1)
                    self.assertIn("meteor_spa", err)


# --------------------------------------------------------------- constants -

class ConstantsTests(unittest.TestCase):
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

    def test_retailers_constant(self):
        m = _import_module()
        self.assertEqual(set(m.RETAILERS), {"cold_storage", "fairprice", "sheng_siong"})


if __name__ == "__main__":
    unittest.main()
