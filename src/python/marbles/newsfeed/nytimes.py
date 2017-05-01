from bs4 import BeautifulSoup
from scraper import AbsractScraper, RssFeed
import time


NYTIMES_HomePageUS = 'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml'
NYTIMES_World = 'http://www.nytimes.com/services/xml/rss/nyt/World.xml'
NYTIMES_World_AtWarBlog = 'http://atwar.blogs.nytimes.com/feed/'
NYTIMES_World_Africa = 'http://www.nytimes.com/services/xml/rss/nyt/Africa.xml'
NYTIMES_World_Americas = 'http://www.nytimes.com/services/xml/rss/nyt/Americas.xml'
NYTIMES_World_AsiaPacific = 'http://www.nytimes.com/services/xml/rss/nyt/AsiaPacific.xml'
NYTIMES_World_Europe = 'http://www.nytimes.com/services/xml/rss/nyt/Europe.xml'
NYTIMES_World_MiddleEast = 'http://www.nytimes.com/services/xml/rss/nyt/MiddleEast.xml'
NYTIMES_US = 'http://www.nytimes.com/services/xml/rss/nyt/US.xml'
NYTIMES_US_Education = 'http://www.nytimes.com/services/xml/rss/nyt/Education.xml'
NYTIMES_US_Politics = 'http://www.nytimes.com/services/xml/rss/nyt/Politics.xml'
NYTIMES_US_Upshot = 'http://www.nytimes.com/services/xml/rss/nyt/Upshot.xml'
NYTIMES_NYRegion = 'http://www.nytimes.com/services/xml/rss/nyt/NYRegion.xml'
NYTIMES_Business = 'http://feeds.nytimes.com/nyt/rss/Business.xml'
NYTIMES_Business_EnergyEnvironment = 'http://www.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml'
NYTIMES_Business_SmallBusiness = 'http://www.nytimes.com/services/xml/rss/nyt/SmallBusiness.xml'
NYTIMES_Business_Economy = 'http://www.nytimes.com/services/xml/rss/nyt/Economy.xml'
NYTIMES_Business_DealBook = 'http://www.nytimes.com/services/xml/rss/nyt/Dealbook.xml'
NYTIMES_Business_MediaAdvertising = 'http://www.nytimes.com/services/xml/rss/nyt/MediaandAdvertising.xml'
NYTIMES_Business_YourMoney = 'http://www.nytimes.com/services/xml/rss/nyt/YourMoney.xml'
NYTIMES_Technology = 'http://feeds.nytimes.com/nyt/rss/Technology.xml'
NYTIMES_Technology_Personal = 'http://rss.nytimes.com/services/xml/rss/nyt/PersonalTech.xml'
NYTIMES_Sports = 'http://www.nytimes.com/services/xml/rss/nyt/Sports.xml'
NYTIMES_Sports_Baseball = 'http://www.nytimes.com/services/xml/rss/nyt/Baseball.xml'
NYTIMES_Sports_CollegeBasketball = 'http://www.nytimes.com/services/xml/rss/nyt/CollegeBasketball.xml'
NYTIMES_Sports_CollegeFootball = 'http://www.nytimes.com/services/xml/rss/nyt/CollegeFootball.xml'
NYTIMES_Sports_Golf = 'http://www.nytimes.com/services/xml/rss/nyt/Golf.xml'
NYTIMES_Sports_Hockey = 'http://www.nytimes.com/services/xml/rss/nyt/Hockey.xml'
NYTIMES_Sports_ProBasketball = 'http://www.nytimes.com/services/xml/rss/nyt/ProBasketball.xml'
NYTIMES_Sports_ProFootball = 'http://www.nytimes.com/services/xml/rss/nyt/.xml'
NYTIMES_Sports_Soccer = 'http://www.nytimes.com/services/xml/rss/nyt/Soccer.xml'
NYTIMES_Sports_Tennis = 'http://www.nytimes.com/services/xml/rss/nyt/Tennis.xml'
NYTIMES_Sports_Gambit = 'http://gambit.blogs.nytimes.com/feed/'
NYTIMES_Science = 'http://www.nytimes.com/services/xml/rss/nyt/Science.xml'
NYTIMES_Science_Environment = 'http://www.nytimes.com/services/xml/rss/nyt/Environment.xml'
NYTIMES_Science_Space = 'http://www.nytimes.com/services/xml/rss/nyt/Space.xml'
NYTIMES_Health = 'http://www.nytimes.com/services/xml/rss/nyt/Health.xml'
NYTIMES_Health_WellBlog = 'http://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/well/rss.xml'
NYTIMES_Health_Research = 'http://www.nytimes.com/services/xml/rss/nyt/Research.xml'
NYTIMES_Health_Nutrition = 'http://www.nytimes.com/services/xml/rss/nyt/Nutrition.xml'
NYTIMES_Health_HealthCarePolicy = 'http://www.nytimes.com/services/xml/rss/nyt/HealthCarePolicy.xml'
NYTIMES_Health_Views = 'http://www.nytimes.com/services/xml/rss/nyt/Views.xml'

NYTIMES_Arts = 'http://www.nytimes.com/services/xml/rss/nyt/Arts.xml'
NYTIMES_Arts_ArtandDesign = 'http://www.nytimes.com/services/xml/rss/nyt/ArtandDesign.xml'
NYTIMES_Arts_Books = 'http://www.nytimes.com/services/xml/rss/nyt/Books.xml'
NYTIMES_Arts_Dance = 'http://www.nytimes.com/services/xml/rss/nyt/Dance.xml'
NYTIMES_Arts_Movies = 'http://www.nytimes.com/services/xml/rss/nyt/Movies.xml'
NYTIMES_Arts_Music = 'http://www.nytimes.com/services/xml/rss/nyt/Music.xml'
NYTIMES_Arts_Television = 'http://www.nytimes.com/services/xml/rss/nyt/Television.xml'
NYTIMES_Arts_Theater = 'http://www.nytimes.com/services/xml/rss/nyt/Theater.xml'
NYTIMES_Arts_CarpetBagger = 'https://carpetbagger.blogs.nytimes.com/feed/'
#NYTIMES_Style (7 RSS feeds)
#NYTIMES_Travel (3 RSS feeds)
#NYTIMES_Magazine (1 RSS feed)

NYTIMES_Jobs = 'http://www.nytimes.com/services/xml/rss/nyt/JobMarket.xml'
NYTIMES_RealEstate = 'http://www.nytimes.com/services/xml/rss/nyt/RealEstate.xml'
NYTIMES_RealEstate_Commercial = 'http://www.nytimes.com/services/xml/rss/nyt/Commercial.xml'
NYTIMES_Autos = 'http://www.nytimes.com/services/xml/rss/nyt/Automobiles.xml'

#NYTIMES_After Deadline Blog
#NYTIMES_Lens Blog
#NYTIMES_The Public Editor (1 RSS feed)
#NYTIMES_Wordplay Blog
#NYTIMES_Obituaries
#NYTIMES_Times Wire
#NYTIMES_Most E-Mailed
#NYTIMES_Most Shared
#NYTIMES_Most Viewed

#NYTIMES_Columnists (18 RSS feeds)
#NYTIMES_Editorials
#NYTIMES_Op-Eds
#NYTIMES_Opinionator (25 RSS feeds)
#NYTIMES_Blogs (3 RSS feeds)
#NYTIMES_Sunday Review
#NYTIMES_Letters
#NYTIMES_Video

_ALLFEEDS = [
    NYTIMES_HomePageUS,
    NYTIMES_World,
    NYTIMES_World_AtWarBlog,
    NYTIMES_World_Africa,
    NYTIMES_World_Americas,
    NYTIMES_World_AsiaPacific,
    NYTIMES_World_Europe,
    NYTIMES_World_MiddleEast,
    NYTIMES_US,
    NYTIMES_US_Education,
    NYTIMES_US_Politics,
    NYTIMES_US_Upshot,
    NYTIMES_NYRegion,
    NYTIMES_Business,
    NYTIMES_Business_EnergyEnvironment,
    NYTIMES_Business_SmallBusiness,
    NYTIMES_Business_Economy,
    NYTIMES_Business_DealBook,
    NYTIMES_Business_MediaAdvertising,
    NYTIMES_Business_YourMoney,
    NYTIMES_Technology,
    NYTIMES_Technology_Personal,
    NYTIMES_Sports,
    NYTIMES_Sports_Baseball,
    NYTIMES_Sports_CollegeBasketball,
    NYTIMES_Sports_CollegeFootball,
    NYTIMES_Sports_Golf,
    NYTIMES_Sports_Hockey,
    NYTIMES_Sports_ProBasketball,
    NYTIMES_Sports_ProFootball,
    NYTIMES_Sports_Soccer,
    NYTIMES_Sports_Tennis,
    NYTIMES_Sports_Gambit,
    NYTIMES_Science,
    NYTIMES_Science_Environment,
    NYTIMES_Science_Space,
    NYTIMES_Health,
    NYTIMES_Health_WellBlog,
    NYTIMES_Health_Research,
    NYTIMES_Health_Nutrition,
    NYTIMES_Health_HealthCarePolicy,
    NYTIMES_Health_Views,
    NYTIMES_Arts,
    NYTIMES_Arts_ArtandDesign,
    NYTIMES_Arts_Books,
    NYTIMES_Arts_Dance,
    NYTIMES_Arts_Movies,
    NYTIMES_Arts_Music,
    NYTIMES_Arts_Television,
    NYTIMES_Arts_Theater,
    NYTIMES_Arts_CarpetBagger,
    NYTIMES_Jobs,
    NYTIMES_RealEstate,
    NYTIMES_RealEstate_Commercial,
    NYTIMES_Autos,
]

class NYTimesScraper(AbsractScraper):
    '''Scraper for Reuters news articles.'''
    def __init__(self, *args, **kwargs):
        super(NYTimesScraper, self).__init__(*args, **kwargs)
        self.count = 5

    def get_article_text(self, url):
        """Scrape the article text.

        Args:
            url: The article url.

        Returns:
            A string.
        """
        self.browser.get(url)
        soup = BeautifulSoup(self.browser.page_source, "html.parser")
        article = soup.select('p.story-body-text.story-content')
        text = []
        for p in article:
            text.append(p.text)
        self.count -= 1
        if self.count == 0:
            # Nytimes only allows reading of 8 articles so discard cookies regularly
            self.browser.delete_all_cookies()
            self.count = 5
        return '\n'.join(text)

    @classmethod
    def get_rss_feed_list(cls):
        """Returns a list of tuples of (feed-name, feed-url)."""
        return _ALLFEEDS


if __name__ == '__main__':
    rss = RssFeed(NYTIMES_US_Politics)
    scraper = NYTimesScraper()
    print(rss.feed.title)
    articles = rss.get_articles()
    for a in articles:
        print(a.title)
        print('='*len(a.title))
        print(a.summary)
        print('--begin-body--')
        text = scraper.get_article_text(a.link)
        print(text)
        time.sleep(1)
        print('--end-body--')
