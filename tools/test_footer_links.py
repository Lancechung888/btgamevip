import unittest
from check_footer_links import ArticleFooter


class FooterLinkTests(unittest.TestCase):
    def parse(self, content):
        page = ArticleFooter()
        page.feed('<article class="post h-entry">Article</article>' + content)
        return page

    def test_plain_names_and_invisible_data_are_not_links(self):
        page = self.parse('<footer class="site-footer"><data class="u-url" href="/"></data><h2 class="footer-heading">Site</h2><li class="p-name">Site</li></footer>')
        self.assertEqual(len(page.errors()), 2)

    def test_named_real_links_pass(self):
        page = self.parse('<footer class="site-footer"><h2 class="footer-heading"><a href="/">Site</a></h2><li class="p-name"><a href="/">Site</a></li></footer>')
        self.assertEqual(page.errors(), [])

    def test_wrong_empty_and_placeholder_links_fail(self):
        for href, label in [("#", "Site"), ("/missing/", "Site"), ("javascript:void(0)", "Site"), ("/", "")]:
            page = self.parse(f'<footer class="site-footer"><h2 class="footer-heading"><a href="{href}">{label}</a></h2></footer>')
            self.assertEqual(len(page.errors()), 2)

    def test_other_navigation_does_not_hide_a_missing_footer(self):
        page = self.parse('<header><a href="/">Site</a></header>')
        self.assertEqual(page.errors(), ["article has no shared footer"])


if __name__ == "__main__":
    unittest.main()
