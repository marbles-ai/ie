# The future import will convert all strings to unicode.
from __future__ import unicode_literals, print_function
import os
from bs4 import BeautifulSoup
from selenium import webdriver
import feedparser
import datetime
import email.utils
import re
import hashlib


# PhantomJS files have different extensions
# under different operating systems
_PHANTOMJS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phantomjs')
_DATE1 = re.compile(r'/(?P<year>\d\d\d\d)/(?P<month>\d\d)/(?P<day>\d\d)/')
_DOM = re.compile(r'https?://(?P<domain>[a-zA-Z0-9.-]+)(?:/.*)?$')

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

    def get_aws_s3_names(self, article_text):
        """Get the s3 names for the article.

        Returns:
            A tuple of s3 bucket and a unique article id.
        """
        global _DOM
        if isinstance(article_text, unicode):
            article_text = article_text.encode('utf-8')
        title = self.entry.title
        if isinstance(title, unicode):
            title = title.encode('utf-8')
        name = '-'.join(map(lambda x: x.lower().strip('?.,:; '), title.split(' ')))
        dt = '{:%Y/%m/%d}'.format(self.get_date())
        m = _DOM.match(self.entry.link)
        assert m is not None
        dom = m.group('domain').replace('.', '-')
        h = hashlib.md5()
        if isinstance(dom, unicode):
            dom = dom.encode('utf8')
        if isinstance(name, unicode):
            name = name.encode('utf8')
        if isinstance(article_text, unicode):
            article_text = article_text.encode('utf8')
        h.update(dom)
        h.update(name)
        h.update(article_text)
        h = h.hexdigest()
        return (dom, name + '/' + dt + '/' + h)

    def get_date(self, default_now=True):
        global _DATE1
        if hasattr(self.entry, 'updated'):
            return datetime.datetime.utcfromtimestamp(
                email.utils.mktime_tz(email.utils.parsedate_tz(self.entry.updated)))
        # Check if the date is in the URL
        m = _DATE1.match(self.entry.link)
        now = datetime.datetime.today()
        if m is not None:
            dt = datetime.datetime(year=int(m.group('year')), month=int(m.group('month')),
                                   day=int(m.group('day')), tz=now.tzinfo)
            return dt
        return None if not default_now else datetime.datetime.today()

    def copy_to_aws(self):
        """Copy the article to AWS."""
        bucket, name = self.get_aws_s3_names()
        print('%s/%s' % (bucket, name))



class RssFeed(object):
    """RSS Feed"""
    def __init__(self, link, max_retries=3):
        self._rss = feedparser.parse(link)
        self._ids_read = set()
        self._retries = {}
        self._max_retries = max_retries

    def check_isread(self, entry_id):
        """Check if an entry has been read."""
        # TODO: check external db if not in memory cache
        if entry_id in self._ids_read:
            return True
        # Don't read if we failed max_retries
        if entry_id in self._retries:
            return self._retries[entry_id] >= self._max_retries

    def get_articles(self, mark_as_read=True, ignore_read=True):
        articles = []
        # FIXME: item.guid maps to id and RSS spec says item.guid is optional
        for entry in self._rss.entries:
            try:
                if ignore_read and self.check_isread(entry.id):
                    # Ignore read articles
                    continue
                articles.append(Article(entry))
                if mark_as_read:
                    self._ids_read.add(entry.id)
            except Exception:
                self._retries.setdefault(entry.id, 0)
                self._retries[entry.id] += 1

        return articles

    @property
    def feed(self):
        return self._rss.feed
