import unittest
from types import SimpleNamespace
from unittest.mock import ANY, patch

from cpa_xai import browser_confirm


class BrowserReuseTests(unittest.TestCase):
    def test_successful_reusable_browser_is_released_without_closing(self):
        browser = object()
        page = object()
        session = SimpleNamespace(
            user_code="ABC",
            device_code="device-code",
            interval=5,
            expires_in=300,
            verification_uri_complete="https://example.com/device",
        )
        token = SimpleNamespace(
            access_token="a",
            refresh_token="r",
            id_token="i",
            token_type="Bearer",
            expires_in=3600,
        )

        with patch("cpa_xai.oauth_device.request_device_code", return_value=session), patch(
            "cpa_xai.oauth_device.poll_device_token", return_value=token
        ), patch.object(
            browser_confirm, "acquire_mint_browser", return_value=(browser, page, False)
        ), patch.object(browser_confirm.time, "sleep"), patch.object(
            browser_confirm, "approve_device_code"
        ), patch.object(
            browser_confirm, "release_mint_browser"
        ) as release, patch.object(browser_confirm, "close_standalone") as close:
            result = browser_confirm.mint_with_browser(email="a@example.com", password="secret")

        self.assertEqual(result["access_token"], "a")
        close.assert_not_called()
        release.assert_called_once_with(owned=False, success=True, log=ANY)


if __name__ == "__main__":
    unittest.main()
