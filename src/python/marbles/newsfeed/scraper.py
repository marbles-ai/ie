# The future import will convert all strings to unicode.
#from __future__ import unicode_literals, print_function
from __future__ import unicode_literals, print_function
import os
from bs4 import BeautifulSoup
from selenium import webdriver
import feedparser
import datetime
import email.utils
import re
import hashlib
import weakref
import platform
from marbles import safe_utf8_encode, safe_utf8_decode, future_string


# PhantomJS files have different extensions
# under different operating systems
if platform.system().lower() == 'darwin':
    PHANTOMJS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phantomjs-osx')
elif platform.dist()[0].lower() == 'ubuntu':
    PHANTOMJS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phantomjs-ubuntu')
else: # Generic linux
    PHANTOMJS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phantomjs-linux')


_DATE1 = re.compile(r'/(?P<year>\d\d\d\d)/(?P<month>\d\d)/(?P<day>\d\d)/')
_DOM = re.compile(r'https?://(?:ww[^.]*\.)?(?P<domain>[a-zA-Z0-9.-]+)(?:/.*)?$')
_NALNUMSP = re.compile(r'[^A-Za-z0-9 _-]')


class Browser(object):
    """Browser wrapper allows cookie counting and can be shared amongst many scrapers."""
    def __init__(self, ghost_log_file=None, firefox=False):
        if firefox:
            # Visual display in firefox
            self.driver = webdriver.FireFox()
        else:
            #driver = webdriver.PhantomJS(service_log_path='/var/log/phantomjs/ghostdriver.log')
            self.driver = webdriver.PhantomJS(PHANTOMJS_PATH, service_log_path=ghost_log_file)
        self.scrapers = []

    @property
    def page_source(self):
        return self.driver.page_source

    def register_scraper(self, scraper):
        self.scrapers.append(weakref.ref(scraper))

    def get_blank(self):
        self.driver.get('about:blank')

    def get(self, url):
        return self.driver.get(url)

    def delete_all_cookies(self):
        self.driver.delete_all_cookies()
        for wr in self.scrapers:
            wr().reset_cookie_count()

    def close(self):
        self.driver.close()
        self.driver.quit()
        self.driver = None


class AbsractScraper(object):
    """Web Scraper"""
    def __init__(self, browser=None, max_count=0):
        if browser:
            self.browser = browser
            self.can_close_browser = False
        else:
            self.browser = Browser()
            self.can_close_browser = True
        self.max_count = max_count
        self.count = max_count
        self.browser.register_scraper(self)

    def reset_cookie_count(self):
        self.count = self.max_count

    def cookie_count(self):
        self.count -= 1
        if self.count <= 0:
            self.browser.delete_all_cookies()
            self.count = self.max_count

    def close(self):
        if self.can_close_browser and self.browser:
            self.browser.close()

    def get_blank(self):
        self.browser.get('about:blank')

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
        text = text.lower()
        if future_string == unicode:
            return '-'.join(filter(lambda y: len(y) != 0, _NALNUMSP.sub('', text).split(' ')))

        if isinstance(text, unicode):
            text = text.encode('utf-8')
        result = '-'.join(filter(lambda y: len(y) != 0, _NALNUMSP.sub('', text).split(' ')))
        # PWG: don't know why this happens but if text contains unicode
        # it is converted automatically
        return safe_utf8_encode(result)

    def get_aws_s3_names(self, article_text):
        """Get the s3 name for the article.

        Returns:
            A tuple containing the s3 bucket and object-name for the article.
        """
        # FIXME: move to __future__
        global _DOM, _ALPHANUM
        m = _DOM.match(self.entry.link)
        assert m is not None
        if future_string == unicode:
            dom = m.group('domain').replace('.', '-')
            name = self.make_s3_name(self.entry.title)
            dt = self.get_date()
            dtYM = '{:%Y-%m}'.format(dt)
            dtD  = '{:%d}'.format(dt)[::-1]
            h = hashlib.md5()
            language = self.feed.language.lower() if hasattr(self.feed, 'language') else 'en-us'
            h.update(safe_utf8_encode(language))
            h.update(safe_utf8_encode(dom))
            h.update(safe_utf8_encode(name))
            h.update(safe_utf8_encode(article_text))
            h = h.hexdigest()
            feedtitle = self.make_s3_name(self.feed.title) if hasattr(self.feed, 'title') else 'unknown'
            return 'marbles-ai-feeds-%s-%s' % (language, dtYM), '%s/%s/%s/%s/%s' % (dtD, dom, feedtitle, name, h)

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
        content['title'] = self.entry.title if hasattr(self.entry, 'title') else self.summary
        # Summay defaults to title if it does not exist
        content['summary'] = self.summary
        content['link'] = self.link
        story = scraper.get_article_text(self.link)
        content['content'] = story
        content['author'] = self.entry.author if hasattr(self.entry, 'author') else 'anonymous'
        content['id'] = self.entry.id
        content['provider'] = self.feed.link
        # Try to grab an image
        if hasattr(self.entry, 'media_content'):
            media = []
            thumbnail = -1
            thumbnailw = 100000000
            for i in range(len(self.entry.media_content)):
                m = self.entry.media_content[i]
                d = dict(map(lambda y: (y[0], int(y[1]) if y[0] in ['width', 'height'] else y[1]), m.iteritems()))
                w = d.setdefault('width', 0)    # make sure its always there
                if w != 0 and w < thumbnailw:
                    thumbnailw = w
                    thumbnail = i
                media.append(d)
            content['media'] = {
                'content': media
            }
            if thumbnail >= 0:
                content['media']['thumbnail'] = thumbnail


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
        self._rss = feedparser.parse(self._link)

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




