from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "index.html"


class LandingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self._link = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if tag == "a":
            self._link = {"href": attributes.get("href"), "text": "", "class": attributes.get("class", "")}
            self.links.append(self._link)

    def handle_endtag(self, tag):
        if tag == "a":
            self._link = None

    def handle_data(self, data):
        if self._link is not None:
            self._link["text"] += data


class LandingPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.parser = LandingParser()
        cls.parser.feed(cls.html)
        cls.text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cls.html)).strip()

    def test_document_has_french_language_and_single_h1(self):
        self.assertRegex(self.html, r'<html\s+lang="fr">')
        self.assertEqual(len(re.findall(r"<h1(?:\s|>)", self.html)), 1)
        self.assertIn('href="#contenu">Aller au contenu</a>', self.html)

    def test_all_internal_links_have_a_target(self):
        fragments = [link["href"][1:] for link in self.parser.links if link["href"].startswith("#")]
        self.assertTrue(fragments)
        self.assertEqual([fragment for fragment in fragments if fragment not in self.parser.ids], [])

    def test_no_unapproved_or_broken_commercial_destination(self):
        hrefs = [link["href"] for link in self.parser.links]
        self.assertFalse(any(href is None or not href.strip() for href in hrefs))
        self.assertFalse(any(href.lower().startswith("mailto:") for href in hrefs))
        external = [href for href in hrefs if urlsplit(href).scheme in {"http", "https"}]
        self.assertEqual(external, [])

    def test_primary_ctas_use_the_required_label(self):
        primary_ctas = [
            " ".join(link["text"].split())
            for link in self.parser.links
            if "button" in link["class"].split() and link["href"] == "#candidature"
        ]
        self.assertGreaterEqual(len(primary_ctas), 3)
        self.assertEqual(set(primary_ctas), {"Demander l’accès"})

    def test_offer_and_selection_copy_are_present(self):
        required = (
            "1M€ par an minimum",
            "office hour hebdomadaire",
            "Accès prioritaire aux événements KP",
            "2,5K€ HT / mois",
            "Engagement minimum 3 mois",
            "12K€ HT",
            "Engagement de 6 mois",
            "réponds par le canal privé qui t’a transmis cette page",
        )
        for copy in required:
            with self.subTest(copy=copy):
                self.assertIn(copy, self.text)

    def test_page_avoids_pressure_and_fake_social_proof(self):
        forbidden = (
            "places limitées",
            "dernière chance",
            "offre expire",
            "témoignage",
            "ils nous font confiance",
        )
        lower_text = self.text.lower()
        for copy in forbidden:
            with self.subTest(copy=copy):
                self.assertNotIn(copy, lower_text)

    def test_application_questions_are_an_ordered_list(self):
        self.assertRegex(self.html, r'<ol class="questions">[\s\S]*?</ol>')
        self.assertEqual(len(re.findall(r'<li class="question">', self.html)), 6)


if __name__ == "__main__":
    unittest.main()
