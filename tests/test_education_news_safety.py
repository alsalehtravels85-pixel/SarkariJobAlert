import ast
import unittest
from pathlib import Path


class EducationNewsSafetyTests(unittest.TestCase):
    def test_rss_items_are_saved_as_drafts(self):
        source = Path("scripts/fetch_education_news.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        statuses = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "status":
                        if isinstance(value, ast.Constant):
                            statuses.append(value.value)
        self.assertIn("draft", statuses)
        self.assertNotIn("published", statuses)

    def test_rss_refresh_does_not_delete_existing_articles(self):
        source = Path("scripts/fetch_education_news.py").read_text(encoding="utf-8")
        self.assertNotIn("requests.delete(", source)
        self.assertNotIn("session.delete(", source)


if __name__ == "__main__":
    unittest.main()
