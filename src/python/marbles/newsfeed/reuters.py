from bs4 import BeautifulSoup
from .scraper import AbsractScraper, RssFeed


# Reuters News RSS Feeds
REUTERS_RSS_Arts = 'http://feeds.reuters.com/news/artsculture'
REUTERS_RSS_Business = 'http://feeds.reuters.com/reuters/businessNews'
REUTERS_RSS_Company_News = 'http://feeds.reuters.com/reuters/companyNews'
REUTERS_RSS_Entertainment = 'http://feeds.reuters.com/reuters/entertainment'
REUTERS_RSS_Environment = 'http://feeds.reuters.com/reuters/environment'
REUTERS_RSS_Health_News = 'http://feeds.reuters.com/reuters/healthNews'
REUTERS_RSS_Lifestyle = 'http://feeds.reuters.com/reuters/lifestyle'
REUTERS_RSS_Money = 'http://feeds.reuters.com/news/wealth'
REUTERS_RSS_Most_Read_Articles = 'http://feeds.reuters.com/reuters/MostRead'
REUTERS_RSS_Oddly_Enough = 'http://feeds.reuters.com/reuters/oddlyEnoughNews'
REUTERS_RSS_Pictures = 'http://feeds.reuters.com/ReutersPictures'
REUTERS_RSS_People = 'http://feeds.reuters.com/reuters/peopleNews'
REUTERS_RSS_Politics = 'http://feeds.reuters.com/Reuters/PoliticsNews'
REUTERS_RSS_Science = 'http://feeds.reuters.com/reuters/scienceNews'
REUTERS_RSS_Sports = 'http://feeds.reuters.com/reuters/sportsNews'
REUTERS_RSS_Technology = 'http://feeds.reuters.com/reuters/technologyNews'
REUTERS_RSS_Top_News = 'http://feeds.reuters.com/reuters/topNews'
REUTERS_RSS_US_News = 'http://feeds.reuters.com/Reuters/domesticNews'
REUTERS_RSS_World = 'http://feeds.reuters.com/Reuters/worldNews'

_ALLFEEDS = [
    REUTERS_RSS_Arts,
    REUTERS_RSS_Business,
    REUTERS_RSS_Company_News,
    REUTERS_RSS_Entertainment,
    REUTERS_RSS_Environment,
    REUTERS_RSS_Health_News,
    REUTERS_RSS_Lifestyle,
    REUTERS_RSS_Money,
    REUTERS_RSS_Most_Read_Articles,
    REUTERS_RSS_Oddly_Enough,
    REUTERS_RSS_Pictures,
    REUTERS_RSS_People,
    REUTERS_RSS_Politics,
    REUTERS_RSS_Science,
    REUTERS_RSS_Sports,
    REUTERS_RSS_Technology,
    REUTERS_RSS_Top_News,
    REUTERS_RSS_US_News,
    REUTERS_RSS_World
]


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
        text = []
        for a in article:
            paragraphs = a.find_all('p')
            for p in paragraphs:
                text.append(p.text)
        return '\n'.join(text)

    @classmethod
    def get_rss_feed_list(cls):
        """Returns a list of feed urls."""
        return _ALLFEEDS


if __name__ == '__main__':
    rss = RssFeed(REUTERS_RSS_Politics)
    scraper = ReutersScraper()
    print(rss.feed.title)
    articles = rss.get_articles()
    for a in articles:
        print(a.title)
        print('='*len(a.title))
        print(a.summary)
        print('--begin-body--')
        text = scraper.get_article_text(a.link)
        print(text)
        print('--end-body--')
