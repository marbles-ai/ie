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


# Reuters News RSS Feeds
REUTERS_RSS_Arts = ('Reuters Arts', 'http://feeds.reuters.com/news/artsculture')
REUTERS_RSS_Business = ('Reuters Business', 'http://feeds.reuters.com/reuters/businessNews')
REUTERS_RSS_Company_News = ('Reuters Company News', 'http://feeds.reuters.com/reuters/companyNews')
REUTERS_RSS_Entertainment = ('Reuters Entertainment', 'http://feeds.reuters.com/reuters/entertainment')
REUTERS_RSS_Environment = ('Reuters Environment', 'http://feeds.reuters.com/reuters/environment')
REUTERS_RSS_Health_News = ('Reuters Health News', 'http://feeds.reuters.com/reuters/healthNews')
REUTERS_RSS_Lifestyle = ('Reuters Lifestyle', 'http://feeds.reuters.com/reuters/lifestyle')
REUTERS_RSS_Money = ('Reuters Money', 'http://feeds.reuters.com/news/wealth')
REUTERS_RSS_Most_Read_Articles = ('Reuters Most Read', 'http://feeds.reuters.com/reuters/MostRead')
REUTERS_RSS_Oddly_Enough = ('Reuters Oddly Enough', 'http://feeds.reuters.com/reuters/oddlyEnoughNews')
REUTERS_RSS_Pictures = ('Reuters Pictures', 'http://feeds.reuters.com/ReutersPictures')
REUTERS_RSS_People = ('Reuters People', 'http://feeds.reuters.com/reuters/peopleNews')
REUTERS_RSS_Politics = ('Reuters Politics', 'http://feeds.reuters.com/Reuters/PoliticsNews')
REUTERS_RSS_Science = ('Reuters Science', 'http://feeds.reuters.com/reuters/scienceNews')
REUTERS_RSS_Sports = ('Reuters Sports', 'http://feeds.reuters.com/reuters/sportsNews')
REUTERS_RSS_Technology = ('Reuters Technology', 'http://feeds.reuters.com/reuters/technologyNews')
REUTERS_RSS_Top_News = ('Reuters Top News', 'http://feeds.reuters.com/reuters/topNews')
REUTERS_RSS_US_News = ('Reuters US News', 'http://feeds.reuters.com/Reuters/domesticNews')
REUTERS_RSS_World = ('Reuters World', 'http://feeds.reuters.com/Reuters/worldNews')


class ReutersScraper(AbsractScraper):
    '''Scraper for Reuters news articles.'''
    def __init__(self, *args, **kwargs):
        super(ReutersScraper, self).__init__(*args, **kwargs)

    def get_article_text(self, url):
        """Scrape the article text.

        Args:
            url: The article url.

        Returns:
            A string.
        """
        self.browser.get(url)
        soup = BeautifulSoup(self.browser.page_source, "html.parser")
        article = soup.find_all('span', id='article-text')
        for a in article:
            paragraphs = a.find_all('p')
            for p in paragraphs:
                print(p.text)


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
        self.link = link
        self.ids_read = set()

    def get_articles(self, mark_as_read=True):
        d = feedparser.parse(self.link)
        articles = []
        for entry in d.entries:
            articles.append(Article(entry))
            if mark_as_read:
                self.ids_read.add(entry.id)

        return articles



if __name__ == '__main__':
    rss = RssFeed(REUTERS_RSS_Politics[1])
    scraper = ReutersScraper()
    print(REUTERS_RSS_Politics[0])
    articles = rss.get_articles()
    for a in articles:
        print(a.title)
        print('='*len(a.title))
        print(a.summary)
        print('--begin-body--')
        scraper.get_article_text(a.link)
        print('--end-body--')
