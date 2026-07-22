import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import grok_register_ttk as app
from cpa_xai.browser_confirm import _cookie_banner_visible, dismiss_cookie_banner


class ConfigTests(unittest.TestCase):
    def test_runtime_defaults_match_example(self):
        example = json.loads((Path(__file__).parents[1] / "config.example.json").read_text())
        self.assertEqual(app.DEFAULT_CONFIG, example)

    def test_invalid_config_is_reported(self):
        original = app.config
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            app, "CONFIG_FILE", str(Path(tmp) / "config.json")
        ):
            Path(app.CONFIG_FILE).write_text("{invalid", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "config.json tidak valid"):
                app.load_config()
        app.config = original


class CookieBannerTests(unittest.TestCase):
    def test_requires_strong_cookie_signal(self):
        self.assertFalse(_cookie_banner_visible("I disagree with these terms"))
        self.assertTrue(_cookie_banner_visible("We use cookies to improve this site"))

    def test_dismiss_script_uses_scoped_exact_matching(self):
        class Page:
            def __init__(self):
                self.scripts = []

            def run_js(self, script):
                self.scripts.append(script)
                return "We use cookies" if len(self.scripts) == 1 else "accept all"

        page = Page()
        self.assertTrue(dismiss_cookie_banner(page, lambda _message: None))
        script = page.scripts[1]
        self.assertIn("accept.includes(norm(node))", script)
        self.assertIn("const roots", script)
        self.assertNotIn("norm(node).includes", script)


if __name__ == "__main__":
    unittest.main()
