from __future__ import unicode_literals, print_function
from bs4 import BeautifulSoup
from scraper import AbsractScraper, RssFeed
import time


# Reuters News RSS Feeds
REUTERS_Arts = 'http://feeds.reuters.com/news/artsculture'
REUTERS_Business = 'http://feeds.reuters.com/reuters/businessNews'
REUTERS_Company_News = 'http://feeds.reuters.com/reuters/companyNews'
REUTERS_Entertainment = 'http://feeds.reuters.com/reuters/entertainment'
REUTERS_Environment = 'http://feeds.reuters.com/reuters/environment'
REUTERS_Health_News = 'http://feeds.reuters.com/reuters/healthNews'
REUTERS_Lifestyle = 'http://feeds.reuters.com/reuters/lifestyle'
REUTERS_Money = 'http://feeds.reuters.com/news/wealth'
REUTERS_Most_Read_Articles = 'http://feeds.reuters.com/reuters/MostRead'
REUTERS_Oddly_Enough = 'http://feeds.reuters.com/reuters/oddlyEnoughNews'
REUTERS_Pictures = 'http://feeds.reuters.com/ReutersPictures'
REUTERS_People = 'http://feeds.reuters.com/reuters/peopleNews'
REUTERS_Politics = 'http://feeds.reuters.com/Reuters/PoliticsNews'
REUTERS_Science = 'http://feeds.reuters.com/reuters/scienceNews'
REUTERS_Sports = 'http://feeds.reuters.com/reuters/sportsNews'
REUTERS_Technology = 'http://feeds.reuters.com/reuters/technologyNews'
REUTERS_Top_News = 'http://feeds.reuters.com/reuters/topNews'
REUTERS_US_News = 'http://feeds.reuters.com/Reuters/domesticNews'
REUTERS_World = 'http://feeds.reuters.com/Reuters/worldNews'

_ALLFEEDS = [
    REUTERS_Arts,
    REUTERS_Business,
    REUTERS_Company_News,
    REUTERS_Entertainment,
    REUTERS_Environment,
    REUTERS_Health_News,
    REUTERS_Lifestyle,
    REUTERS_Money,
    REUTERS_Most_Read_Articles,
    REUTERS_Oddly_Enough,
    REUTERS_Pictures,
    REUTERS_People,
    REUTERS_Politics,
    REUTERS_Science,
    REUTERS_Sports,
    REUTERS_Technology,
    REUTERS_Top_News,
    REUTERS_US_News,
    REUTERS_World
]


class ReutersScraper(AbsractScraper):
    '''Scraper for Reuters news articles.'''

    def __init__(self, *args, **kwargs):
        super(ReutersScraper, self).__init__(*args, **kwargs)
        # Number of requests before clearing cookies
        self.count = self.max_count = 5

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
        text = []
        for a in article:
            paragraphs = a.find_all('p')
            for p in paragraphs:
                text.append(p.text)
        self.cookie_count()
        return '\n'.join(text)

    @classmethod
    def get_rss_feed_list(cls):
        """Returns a list of feed urls."""
        return _ALLFEEDS


if __name__ == '__main__':
    rss = RssFeed(REUTERS_Politics)
    scraper = ReutersScraper()
    print(rss.feed.title)
    articles = rss.get_articles()
    for a in articles:
        print(a.title)
        print('='*len(a.title))
        print(a.link)
        print(a.summary)
        print('--begin-body--')
        text = scraper.get_article_text(a.link)
        print(text)
        time.sleep(1)
        print('--end-body--')
