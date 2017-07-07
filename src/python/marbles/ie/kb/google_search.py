# The future import will convert all strings to unicode.
from __future__ import unicode_literals, print_function
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
import logging
from marbles.newsfeed.scraper import PHANTOMJS_PATH


_logger = logging.getLogger(__name__)


_WS = re.compile(r'\s+')


def create_headless_browser(ghost_log_file=None):
    return webdriver.PhantomJS(PHANTOMJS_PATH, service_log_path=ghost_log_file)


class GoogleScraper(object):
    def __init__(self, browser=None, ghost_log_file=None):
        if browser is None:
            self.browser = webdriver.PhantomJS(PHANTOMJS_PATH, service_log_path=ghost_log_file)
        else:
            self.browser = browser

    def search(self, search_string, site=None):
        """Search using Google and scrape the search text.

        Args:
            search_string: The search string.
            site: The site string

        Returns:
            A list of urls.
        """
        global _logger
        # <input class="lst lst-tbb gsfi" id="lst-ib" maxlength="2048" name="q" autocapitalize="off" autocomplete="off" autocorrect="off" title="" type="search" value="" aria-label="Search" aria-haspopup="false" role="combobox" aria-autocomplete="both" dir="ltr" spellcheck="false" style="outline: none;">
        self.browser.delete_all_cookies()
        search_string = _WS.sub(' ', search_string)
        if site:
            search_string += ' site:' + site
        self.browser.get('http://www.google.com')
        wait = WebDriverWait(self.browser, 10)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input.lst')))
            inp = self.browser.find_element_by_css_selector('input.lst')
            inp.send_keys(search_string + '\n')
            wait.until(EC.presence_of_element_located((By.ID, 'lfootercc')))
            #wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h3.r')))
            soup = BeautifulSoup(self.browser.page_source, "lxml")
            links = []
            for item in soup.find_all('h3', attrs={'class' : 'r'}):
                links.append(item.a['href'][7:].split('&')[0]) # [7:] strips the /url?q= prefix
            # Check spelling errors
            spell = self.browser.find_element_by_css_selector('a.spell')
            if spell:
                if site:
                    spell = spell.text.replace(' site:' + site, '').strip()
                else:
                    spell = spell.text.strip()
                if len(spell) == 0:
                    spell = None
            return spell, links
        except TimeoutException as e:
            _logger.warning(str(e))
        return None, []


if __name__ == '__main__':
    gsrch = GoogleScraper()
    urls = gsrch.search('Thomas Jefferson', 'wikipedia.com')
    for url in urls:
        print(url)
