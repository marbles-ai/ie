#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
from optparse import OptionParser


# Modify python path if in development mode
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.dirname(os.path.dirname(thisdir))
if os.path.exists(os.path.join(srcdir, 'marbles', 'ie')):
    sys.path.insert(0, srcdir)
terminate = False


from marbles import newsfeed as nf
from marbles.aws import svc


class NewsSource(object):
    """A news source consists of a scraper and a list of feeds."""
    
    def __init__(self, scraper, feed_urls=None):
        self.scraper = scraper
        feed_urls = feed_urls if feed_urls is not None else scraper.get_rss_feed_list()
        self.feeds = [nf.scraper.RssFeed(u) for u in feed_urls]


class NewsReaderExecutor(svc.ServiceExecutor):

    def __init__(self, state, news_queue_name, oneshot, ghost_log_file=None):
        super(NewsReaderExecutor, self).__init__(wakeup=5*60, state_or_logger=state)
        self.archivers = None
        self.news_queue_name = news_queue_name
        self.ignore_read = True
        self.init_done = False
        self.oneshot = oneshot
        self.ghost_log_file = ghost_log_file
        self.browser = None

    def on_start(self, workdir):
        # If we run multiple theads then each thread needs its own AWS resources (S3, SQS etc).
        aws = AwsNewsQueueWriterResources(self.news_queue_name)
        # Browser creates a single process for this archive
        self.browser = nf.scraper.Browser(ghost_log_file=self.ghost_log_file)
        sources = [
            NewsSource(nf.washingtonpost.WPostScraper(self.browser), [nf.washingtonpost.WPOST_Politics]),
            NewsSource(nf.nytimes.NYTimesScraper(self.browser), [nf.nytimes.NYTIMES_US_Politics]),
            NewsSource(nf.reuters.ReutersScraper(self.browser), [nf.reuters.REUTERS_Politics]),
            NewsSource(nf.foxnews.FoxScraper(self.browser), [nf.foxnews.FOX_Politics]),
        ]

        self.archivers = [
            AwsNewsQueueWriter(aws, state, sources, self.browser),
        ]

    def on_term(self, graceful):
        self.archivers = []
        self.browser.close()

    def on_hup(self):
        self.ignore_read = False
        for arc in self.archivers:
            arc.retire_hash_cache(0)    # clears hash cache
            arc.clear_bucket_cache()

    def on_wake(self):
        if self.init_done:
            # Refresh RSS feeds
            for arc in self.archivers:
                arc.refresh()

        for arc in self.archivers:
            arc.read_all(self.ignore_read)
            # Keep hash cache size in range 4096-8192
            if len(arc.hash_cache) >= 8192:
                arc.retire_hash_cache(4096)
        self.init_done = True
        self.ignore_read = True
        if self.oneshot:
            self.force_terminate()


if __name__ == '__main__':
    usage = 'Usage: %prog [options] [aws-queue-name]'
    parser = OptionParser(usage)
    parser.add_option('-R', '--force-read', action='store_true', dest='force_read', default=False,
                      help='Force read.')
    parser.add_option('-X', '--one-shot', action='store_true', dest='oneshot', default=False,
                      help='Exit after first sync completes.')
    svc.init_parser_options(parser)

    (options, args) = parser.parse_args()

    # Delay import so help is displayed quickly
    from marbles.aws import AwsNewsQueueWriterResources, AwsNewsQueueWriter

    # Setup logging
    svc_name = os.path.splitext(os.path.basename(__file__))[0]
    state = svc.process_parser_options(options, svc_name)
    queue_name = args[0] if len(args) != 0 else None

    svc = NewsReaderExecutor(state, news_queue_name=queue_name, oneshot=options.oneshot,
                             ghost_log_file=options.ghost_log_file)
    if options.force_read:
        svc.force_hup()
    svc.run(thisdir)



