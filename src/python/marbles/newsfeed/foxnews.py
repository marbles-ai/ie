from bs4 import BeautifulSoup
from scraper import AbsractScraper, RssFeed
import time


FOX_Latest = 'http://feeds.foxnews.com/foxnews/latest?format=xml'
FOX_Politics = 'http://feeds.foxnews.com/foxnews/politics?format=xml'
FOX_Science = 'http://feeds.foxnews.com/foxnews/science?format=xml'
FOX_Sports = 'http://feeds.foxnews.com/foxnews/sports?format=xml'
FOX_Tech = 'http://feeds.foxnews.com/foxnews/tech?format=xml'
FOX_National = 'http://feeds.foxnews.com/foxnews/national'
FOX_World = 'http://feeds.foxnews.com/foxnews/world'
FOX_Business = 'http://feeds.foxnews.com/foxnews/business'
FOX_SciTech = 'http://feeds.foxnews.com/foxnews/scitech'
FOX_Health = 'http://feeds.foxnews.com/foxnews/health'
FOX_Entertainment = 'http://feeds.foxnews.com/foxnews/entertainment'
FOX_Views = 'http://feeds.foxnews.com/foxnews/views'
FOX_Blogs = 'http://feeds.foxnews.com/foxnews/foxblogs'
# Columns
FOX_MikeStrakaGrrr = 'http://feeds.foxnews.com/foxnews/column/grrr'
FOX_PopTarts = 'http://feeds.foxnews.com/foxnews/column/poptarts'
FOX_411 = 'http://feeds.foxnews.com/foxnews/column/fox411'


_ALLFEEDS = [
    FOX_Latest,
    FOX_Politics,
    FOX_Science,
    FOX_Sports,
    FOX_Tech,
    FOX_National,
    FOX_World,
    FOX_Business,
    FOX_SciTech,
    FOX_Health,
    FOX_Entertainment,
    FOX_Views,
    FOX_Blogs,
    FOX_MikeStrakaGrrr,
    FOX_PopTarts,
    FOX_411
]


class FoxScraper(AbsractScraper):
    '''Scraper for Fox news articles.'''

    def __init__(self, *args, **kwargs):
        super(FoxScraper, self).__init__(*args, **kwargs)
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
        article = soup.select('div.article-text')
        text = []
        for a in article:
            paragraphs = a.find_all('p')
            for p in paragraphs:
                text.append(p.text)
        self.cookie_count()
        return '\n'.join(text)

    @classmethod
    def get_rss_feed_list(cls):
        """Returns a list of tuples of feed urls."""
        return _ALLFEEDS


if __name__ == '__main__':
    rss = RssFeed(FOX_Politics)
    scraper = FoxScraper()
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
