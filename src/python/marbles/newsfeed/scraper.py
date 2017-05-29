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
_DOM = re.compile(r'https?://(?:ww[^.]*\.)?(?P<domain>[a-zA-Z0-9.-]+)(?:/.*)?$')
_NALNUMSP = re.compile(r'[^A-Za-z0-9 _-]')


def safe_utf8_encode(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return s


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
    def __init__(self, entry, feed):
        self.entry = entry
        self.feed = feed

    @property
    def title(self):
        """Get the article title."""
        return self.entry.title

    @property
    def summary(self):
        """Get the summary text."""
        if hasattr(self.entry, 'summary'):
            return BeautifulSoup(self.entry.summary, 'lxml').text
        return self.entry.title

    @property
    def link(self):
        """Get the link to the news story."""
        return self.entry.link

    @classmethod
    def make_s3_name(cls, text):
        global _ALPHANUM
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        return '-'.join(filter(lambda y: len(y) != 0, _NALNUMSP.sub('', text).lower().split(' ')))

    def get_aws_s3_names(self, article_text):
        """Get the s3 name for the article.

        Returns:
            A tuple containing the s3 bucket and object-name for the article.
        """
        # FIXME: move to __future__
        global _DOM, _ALPHANUM
        m = _DOM.match(self.entry.link)
        assert m is not None
        dom = safe_utf8_encode(m.group('domain').replace('.', '-'))
        name = self.make_s3_name(self.entry.title)
        dt = self.get_date()
        dtYM = safe_utf8_encode('{:%Y-%m}'.format(dt))
        dtD  = safe_utf8_encode('{:%d}'.format(dt)[::-1])
        h = safe_utf8_encode(hashlib.md5())
        article_text = safe_utf8_encode(article_text)
        name = safe_utf8_encode(name)
        # FIXME: use geo-location on domain to infer language
        language = safe_utf8_encode(self.feed.language.lower()) if hasattr(self.feed, 'language') else 'en-us'
        h.update(language)
        h.update(dom)
        h.update(name)
        h.update(article_text)
        h = h.hexdigest()
        feedtitle = self.make_s3_name(self.feed.title) if hasattr(self.feed, 'title') else 'unknown'
        return 'marbles-ai-feeds-%s-%s' % (language, dtYM), '%s/%s/%s/%s/%s' % (dtD, dom, feedtitle, name, h)

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

    def archive(self, scraper):
        """Archive a story into a dictionary.

        Args:
            scraper: The scraper for this content provider.

        Returns:
            The dictionary. This can be written to s3 storage in json format.
        """
        # RSS must support at least one of summary or title
        content = {}
        content['title'] = safe_utf8_encode(self.title if hasattr(self, 'title') else self.summary)
        # Summay defaults to title if it does not exist
        content['summary'] = safe_utf8_encode(self.summary)
        content['link'] = safe_utf8_encode(self.link)
        story = scraper.get_article_text(self.link)
        content['content'] = safe_utf8_encode(story)
        content['author'] = safe_utf8_encode(self.entry.author) if hasattr(self.entry, 'author') else 'anonymous'
        return content


class RssFeed(object):
    """RSS Feed"""
    def __init__(self, link, max_retries=3):
        self._link = link
        self._rss = feedparser.parse(link)
        self._ids_read = {}
        self._retries = {}
        self._max_retries = max_retries

    def refresh(self):
        self._rss = feedparser.parse(self.link)

    def check_isread(self, entry_id):
        """Check if an entry has been read."""
        # TODO: check external db if not in memory cache
        if entry_id in self._ids_read:
            return True
        # Don't read if we failed max_retries
        if entry_id in self._retries:
            return self._retries[entry_id] >= self._max_retries

    def retire_old_articles(self):
        active = set(map(lambda x: x.id, self._rss.entries))
        self._ids_read = dict(filter(lambda x: x.id in active, self._ids_read))

    def get_articles(self, mark_as_read=True, ignore_read=True):
        articles = []
        # FIXME: item.guid maps to id and RSS spec says item.guid is optional
        for entry in self._rss.entries:
            try:
                if ignore_read and self.check_isread(entry.id):
                    # Ignore read articles
                    continue
                articles.append(Article(entry, self.feed))
                if mark_as_read:
                    # Timestamp
                    self._ids_read[entry.id] = datetime.datetime.today()
            except Exception:
                self._retries.setdefault(entry.id, 0)
                self._retries[entry.id] += 1

        return articles

    @property
    def feed(self):
        return self._rss.feed




