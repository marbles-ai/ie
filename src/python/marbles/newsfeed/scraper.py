# The future import will convert all strings to unicode.
from __future__ import unicode_literals, print_function
import os
from bs4 import BeautifulSoup
from selenium import webdriver
import feedparser


# PhantomJS files have different extensions
# under different operating systems
_PHANTOMJS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phantomjs')


class AbsractScraper(object):
    def __init__(self, firefox=False):
        if firefox:
            # Visual display in firefox
            self.browser = webdriver.FireFox()
        else:
            self.browser = webdriver.PhantomJS(_PHANTOMJS_PATH)

    def get_article_text(self, url):
        """Scrape the article text.

        Args:
            url: The article url.

        Returns:
            A string.
        """
        raise NotImplementedError

    @classmethod
    def get_rss_feed_list(cls):
        """Returns a list of feed urls."""
        return []


class Article(object):
    """RSS Feed Article"""
    def __init__(self, entry):
        self.entry = entry

    @property
    def title(self):
        """Get the article title."""
        return self.entry.title

    @property
    def summary(self):
        """Get the summary text."""
        return BeautifulSoup(self.entry.summary, 'lxml').text

    @property
    def link(self):
        """Get the link to the news story."""
        return self.entry.link


class RssFeed(object):
    """RSS Feed"""
    def __init__(self, link):
        self.rss = feedparser.parse(link)
        self.ids_read = set()

    def get_articles(self, mark_as_read=True):
        articles = []
        for entry in self.rss.entries:
            articles.append(Article(entry))
            if mark_as_read:
                self.ids_read.add(entry.id)

        return articles

    @property
    def feed(self):
        return self.rss.feed
