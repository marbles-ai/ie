from bs4 import BeautifulSoup
from scraper import AbsractScraper, RssFeed
import time


WPOST_Politics = 'http://feeds.washingtonpost.com/rss/politics'
WPOST_Politics_Blog_PostPolitics = 'http://feeds.washingtonpost.com/rss/rss_election-2012'
WPOST_Politics_Blog_PowerPost = 'http://feeds.washingtonpost.com/rss/rss_powerpost'
WPOST_Politics_Blog_FactChecker = 'http://feeds.washingtonpost.com/rss/rss_fact-checker'
WPOST_Politics_Blog_TheFix = 'http://feeds.washingtonpost.com/rss/rss_the-fix'
WPOST_Politics_Blog_MonkeyCage = 'http://feeds.washingtonpost.com/rss/rss_monkey-cage'
WPOST_Opinions = 'http://feeds.washingtonpost.com/rss/opinions'
WPOST_Opinions_Blog_Act4 = 'http://feeds.washingtonpost.com/rss/rss_act-four'
WPOST_Opinions_Blog_AskThePost = 'http://feeds.washingtonpost.com/rss/rss_ask-the-post'
WPOST_Opinions_Blog_AreLocal = 'http://feeds.washingtonpost.com/rss/rss_all-opinions-are-local'
WPOST_Opinions_Blog_ComPost = 'http://feeds.washingtonpost.com/rss/rss_compost'
WPOST_Opinions_Blog_BookParty = 'http://feeds.washingtonpost.com/rss/rss_book-party'
WPOST_Opinions_Blog_ErikWemple = 'http://feeds.washingtonpost.com/rss/rss_erik-wemple'
WPOST_Opinions_Blog_PlumLine = 'http://feeds.washingtonpost.com/rss/rss_plum-line'
WPOST_Opinions_Blog_PostPartisan = 'http://feeds.washingtonpost.com/rss/rss_post-partisan'
WPOST_Opinions_Blog_PostEverything = 'http://feeds.washingtonpost.com/rss/rss_post-everything'
WPOST_Opinions_Blog_Rampage = 'http://feeds.washingtonpost.com/rss/rss_rampage'
WPOST_Opinions_Blog_RightTurn = 'http://feeds.washingtonpost.com/rss/rss_right-turn'
WPOST_Opinions_Blog_InTheory = 'http://feeds.washingtonpost.com/rss/rss_in-theory'
WPOST_Opinions_Blog_TomToles = 'http://feeds.washingtonpost.com/rss/rss_tom-toles'
WPOST_Opinions_Blog_TheWatch = 'http://feeds.washingtonpost.com/rss/rss_the-watch'
WPOST_Opinions_Blog_VolokhConspiracy = 'http://feeds.washingtonpost.com/rss/rss_volokh-conspiracy'
WPOST_Local = 'http://feeds.washingtonpost.com/rss/local'
WPOST_Local_Blog_HouseDivided = 'http://feeds.washingtonpost.com/rss/rss_house-divided'
WPOST_Local_Blog_ActOfFaith = 'http://feeds.washingtonpost.com/rss/rss_acts-of-faith'
WPOST_Local_Blog_AnswerSheet = 'https://www.washingtonpost.com/blogs/answer-sheet/feed/'
WPOST_Local_Blog_CaptialWeatherGang = 'http://feeds.washingtonpost.com/rss/rss_capital-weather-gang'
WPOST_Local_Blog_GradePoint = 'http://feeds.washingtonpost.com/rss/rss_grade-point'
WPOST_Local_Blog_Express = 'http://feeds.washingtonpost.com/rss/rss_express'
WPOST_Local_Blog_InspiredLife = 'http://feeds.washingtonpost.com/rss/national/inspired-life'
WPOST_Local_Blog_Retropolis = 'https://www.washingtonpost.com/news/retropolis/?outputType=rss'
WPOST_Sports = 'http://feeds.washingtonpost.com/rss/sports'
WPOST_Sports_Blog_AllMetSports = 'http://feeds.washingtonpost.com/rss/rss_recruiting-insider'
WPOST_Sports_Blog_DCSportsBog = 'http://feeds.washingtonpost.com/rss/rss_dc-sports-bog'
WPOST_Sports_Blog_EarlyLead = 'http://feeds.washingtonpost.com/rss/rss_early-lead'
WPOST_Sports_Blog_FancyStats = 'http://feeds.washingtonpost.com/rss/rss_fancy-stats'
WPOST_Sports_Blog_TheInsider = 'http://feeds.washingtonpost.com/rss/rss_football-insider'
WPOST_Sports_Blog_MarylandTerrapins = 'http://feeds.washingtonpost.com/rss/rss_terrapins-insider'
WPOST_Sports_Blog_SoccerInsider = 'http://feeds.washingtonpost.com/rss/rss_soccer-insider'
WPOST_Sports_Blog_WashingtonCapitals = 'http://feeds.washingtonpost.com/rss/rss_capitals-insider'
WPOST_Sports_Blog_WashingtonNationals = 'http://feeds.washingtonpost.com/rss/rss_nationals-journal'
WPOST_Sports_Blog_WashingtonWizards = 'http://feeds.washingtonpost.com/rss/rss_wizards-insider'
WPOST_National = 'http://feeds.washingtonpost.com/rss/national'
WPOST_National_Blog_Achenblog = 'http://feeds.washingtonpost.com/rss/rss_achenblog'
WPOST_National_Blog_Checkpoint = 'http://feeds.washingtonpost.com/rss/rss_checkpoint'
WPOST_National_Blog_Innovations = 'http://feeds.washingtonpost.com/rss/rss_innovations'
WPOST_National_Blog_MorningMix = 'http://feeds.washingtonpost.com/rss/rss_morning-mix'
WPOST_National_Blog_PostNation = 'http://feeds.washingtonpost.com/rss/rss_post-nation'
WPOST_National_Blog_SpeakingScience = 'http://feeds.washingtonpost.com/rss/rss_speaking-of-science'
WPOST_National_Blog_Health = 'http://feeds.washingtonpost.com/rss/rss_to-your-health'
WPOST_World = 'http://feeds.washingtonpost.com/rss/world'
WPOST_World_Blog_WorldViews = 'http://feeds.washingtonpost.com/rss/rss_blogpost'
WPOST_Business = 'http://feeds.washingtonpost.com/rss/business'
WPOST_Business_Blog_Digger = 'http://feeds.washingtonpost.com/rss/rss_digger'
WPOST_Business_Blog_EnergyEnvironment = 'http://feeds.washingtonpost.com/rss/national/energy-environment'
WPOST_Business_Blog_OnLeadership = 'http://feeds.washingtonpost.com/rss/rss_on-leadership'
WPOST_Business_Blog_TheSwitch = 'http://feeds.washingtonpost.com/rss/blogs/rss_the-switch'
WPOST_Business_Blog_Wonkblog = 'http://feeds.washingtonpost.com/rss/rss_wonkblog'
WPOST_Lifestyle = 'http://feeds.washingtonpost.com/rss/lifestyle'
WPOST_Lifestyle_Blog_ArtsEntertainment = 'http://feeds.washingtonpost.com/rss/rss_arts-post'
WPOST_Lifestyle_Blog_Soloish = 'http://feeds.washingtonpost.com/rss/rss_soloish'
WPOST_Lifestyle_Blog_ReliableSource = 'http://feeds.washingtonpost.com/rss/rss_reliable-source'


_ALLFEEDS = [
    WPOST_Politics,
    WPOST_Politics_Blog_PostPolitics,
    WPOST_Politics_Blog_PowerPost,
    WPOST_Politics_Blog_FactChecker,
    WPOST_Politics_Blog_TheFix,
    WPOST_Politics_Blog_MonkeyCage,
    WPOST_Opinions,
    WPOST_Opinions_Blog_Act4,
    WPOST_Opinions_Blog_AskThePost,
    WPOST_Opinions_Blog_AreLocal,
    WPOST_Opinions_Blog_ComPost,
    WPOST_Opinions_Blog_BookParty,
    WPOST_Opinions_Blog_ErikWemple,
    WPOST_Opinions_Blog_PlumLine,
    WPOST_Opinions_Blog_PostPartisan,
    WPOST_Opinions_Blog_PostEverything,
    WPOST_Opinions_Blog_Rampage,
    WPOST_Opinions_Blog_RightTurn,
    WPOST_Opinions_Blog_InTheory,
    WPOST_Opinions_Blog_TomToles,
    WPOST_Opinions_Blog_TheWatch,
    WPOST_Opinions_Blog_VolokhConspiracy,
    WPOST_Local,
    WPOST_Local_Blog_HouseDivided,
    WPOST_Local_Blog_ActOfFaith,
    WPOST_Local_Blog_AnswerSheet,
    WPOST_Local_Blog_CaptialWeatherGang,
    WPOST_Local_Blog_GradePoint,
    WPOST_Local_Blog_Express,
    WPOST_Local_Blog_InspiredLife,
    WPOST_Local_Blog_Retropolis,
    WPOST_Sports,
    WPOST_Sports_Blog_AllMetSports,
    WPOST_Sports_Blog_DCSportsBog,
    WPOST_Sports_Blog_EarlyLead,
    WPOST_Sports_Blog_FancyStats,
    WPOST_Sports_Blog_TheInsider,
    WPOST_Sports_Blog_MarylandTerrapins,
    WPOST_Sports_Blog_SoccerInsider,
    WPOST_Sports_Blog_WashingtonCapitals,
    WPOST_Sports_Blog_WashingtonNationals,
    WPOST_Sports_Blog_WashingtonWizards,
    WPOST_National,
    WPOST_National_Blog_Achenblog,
    WPOST_National_Blog_Checkpoint,
    WPOST_National_Blog_Innovations,
    WPOST_National_Blog_MorningMix,
    WPOST_National_Blog_PostNation,
    WPOST_National_Blog_SpeakingScience,
    WPOST_National_Blog_Health,
    WPOST_World,
    WPOST_World_Blog_WorldViews,
    WPOST_Business,
    WPOST_Business_Blog_Digger,
    WPOST_Business_Blog_EnergyEnvironment,
    WPOST_Business_Blog_OnLeadership,
    WPOST_Business_Blog_TheSwitch,
    WPOST_Business_Blog_Wonkblog,
    WPOST_Lifestyle,
    WPOST_Lifestyle_Blog_ArtsEntertainment,
    WPOST_Lifestyle_Blog_Soloish,
    WPOST_Lifestyle_Blog_ReliableSource,
]


class WPostScraper(AbsractScraper):
    '''Scraper for Washington Post news articles.'''
    def __init__(self, *args, **kwargs):
        super(WPostScraper, self).__init__(*args, **kwargs)
        # Number of requests before clearing cookies
        self.count = self.max_count = 2

    def get_article_text(self, url):
        """Scrape the article text.

        Args:
            url: The article url.

        Returns:
            A string.
        """
        self.browser.get(url)
        soup = BeautifulSoup(self.browser.page_source, "html.parser")
        body = soup.find_all('article', itemprop='articleBody')
        text = []
        for b in body:
            paragraphs = b.find_all('p', attrs={'class': None})
            for p in paragraphs:
                text.append(p.text)
        self.cookie_count()
        return '\n'.join(text)

    @classmethod
    def get_rss_feed_list(cls):
        """Returns a list of feed urls."""
        return _ALLFEEDS


if __name__ == '__main__':
    rss = RssFeed(WPOST_Politics)
    scraper = WPostScraper()
    print(rss.feed.title)
    articles = rss.get_articles()
    for a in articles:
        print(a.title)
        print('='*len(a.title))
        print(a.link)
        print(a.summary)
        text = scraper.get_article_text(a.link)
        print('/%s/%s' % a.get_aws_s3_names(text))
        print('--begin-body--')
        print(text)
        time.sleep(1)
        print('--end-body--')
