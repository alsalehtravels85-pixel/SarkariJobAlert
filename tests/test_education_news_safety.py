import ast
import unittest
from pathlib import Path


class EducationNewsSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path("scripts/fetch_education_news.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_qualified_education_news_is_published(self):
        statuses = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "status":
                        if isinstance(value, ast.Constant):
                            statuses.append(value.value)
        self.assertIn("published", statuses)
        self.assertNotIn("draft", statuses)

    def test_cleanup_is_scoped_to_old_education_news_only(self):
        start = self.source.index("def cleanup_old_news():")
        end = self.source.index("\ndef published_news_today():", start)
        cleanup = self.source[start:end]
        self.assertIn('"article_type":"eq.news"', cleanup)
        self.assertIn('"created_at":f"lt.{cutoff}"', cleanup)
        self.assertIn("requests.delete(TABLE", cleanup)
        self.assertNotIn('"article_type":"eq.study_guide"', cleanup)
        self.assertNotIn('"article_type":"eq.vacancy"', cleanup)

    def test_daily_publish_limit_is_checked_before_generation(self):
        self.assertIn("MAX_DAILY=1", self.source)
        self.assertIn("already_published=published_news_today()", self.source)
        self.assertIn("if already_published >= MAX_DAILY:", self.source)
        self.assertIn('"status":"published"', self.source)

    def test_existing_articles_are_not_updated_or_refreshed(self):
        self.assertNotIn("requests.patch(", self.source)
        self.assertNotIn("session.patch(", self.source)


if __name__ == "__main__":
    unittest.main()
