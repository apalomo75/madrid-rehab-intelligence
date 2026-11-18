"""Welcome routing in both languages and deferred access to production data."""

import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from madrid_rehab.navigation import HOME, PRIMARY


class WelcomeTests(unittest.TestCase):
    def test_home_and_cards_in_both_languages(self):
        with (
            patch.dict(
                os.environ,
                {
                    "MADRID_REHAB_PUBLIC": "1",
                    "MADRID_REHAB_OFFLINE": "1",
                    "MADRID_REHAB_DEMO": "0",
                    "MADRID_REHAB_PILOT": "0",
                },
            ),
            patch("madrid_rehab.bundle_delivery.ensure") as ensure,
            patch("madrid_rehab.production_bundle.active", return_value=False),
            patch("madrid_rehab.commercial_catalog_view.render") as explore,
            patch("madrid_rehab.address_view.render") as address,
            patch("madrid_rehab.about_view.render") as about,
        ):
            app = AppTest.from_file("src/madrid_rehab/app.py", default_timeout=60).run()
            self.assertEqual(len(app.button), 3)
            self.assertFalse(any(r.key == "language_selector" for r in app.sidebar.radio))
            self.assertEqual(app.radio(key="language_selector").value, "ES")
            for language, home_label, author in [
                ("ES", "Inicio", "Desarrollado por Alejandro Palomo"),
                ("EN", "Home", "Developed by Alejandro Palomo"),
            ]:
                app.radio(key="language_selector").set_value(language).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.title[0].value, "Madrid Rehab Intelligence")
                self.assertEqual(app.radio(key="city_navigation").options[0], home_label)
                self.assertTrue(any(author in item.value for item in app.markdown))
                self.assertFalse(app.get("deck_gl_json_chart"))
                ensure.assert_not_called()
                for key, route, render in zip(
                    ("welcome_open_explore", "welcome_open_address", "welcome_open_about"),
                    PRIMARY,
                    (explore, address, about),
                    strict=True,
                ):
                    app.button(key=key).click().run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.radio(key="city_navigation").value, route)
                    self.assertEqual(app.sidebar.radio(key="language_selector").value, language)
                    ensure.assert_called_once()
                    render.assert_called_once_with()
                    ensure.reset_mock()
                    render.reset_mock()
                    app.radio(key="city_navigation").set_value(HOME).run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.title[0].value, "Madrid Rehab Intelligence")
                    ensure.assert_not_called()
