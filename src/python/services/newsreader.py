#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import os
import sys
import logging
from optparse import OptionParser
import boto3
import StringIO
import json
import time
from random import shuffle

# Modify python path if in development mode
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.dirname(thisdir)
if os.path.exists(os.path.join('marbles', 'ie')):
    sys.path.insert(0, srcdir)


from marbles.newsfeed import *


class ReaderArchiver(object):
    """RSS/Atom reader archive service."""
    def __init__(self, s3, scrape, logger, feed_urls=None):
        self.s3 = s3
        self.scrape = scrape
        feed_urls = feed_urls if feed_urls is not None else scrape.get_rss_feed_list()
        self.feeds = [scraper.RssFeed(u) for u in feed_urls]
        self.bucket_cache = set()
        self.logger = logger

    def check_bucket_exists(self, bucket):
        if bucket in self.bucket_cache:
            return True
        # Refresh all so we handle deletions
        self.bucket_cache = set()
        for bkt in self.s3.buckets.all():
            self.bucket_cache.add(bkt.name)
        return bucket in self.bucket_cache

    def refresh(self):
        for rss in self.feeds:
            rss.refresh()
            # FIXME: shorter wait
            time.sleep(1)

    def aws_archive(self, ignore_read=True):
        # TODO: randomize access across all feeds to help with rate limiting
        rlimit = {}
        articles = []
        for i in range(len(self.feeds)):
            rss = self.feeds[i]
            articles.extend([(i, a) for a in rss.get_articles(ignore_read=ignore_read)]) # Returns unread articles

        errors = 0
        for i, a in articles:
            try:
                arc = a.archive(self.scrape)
                bucket, objname = a.get_aws_s3_names(arc['content'])
                hash = objname.split('/')[-1]
                exists = 0 != len([x for x in s3.Bucket('marbles-ai-feeds-hash').objects.filter(Prefix=hash)])
                if exists:
                    continue

                if not self.check_bucket_exists(bucket):
                    # Create a bucket
                    self.s3.create_bucket(Bucket=bucket,
                                          CreateBucketConfiguration={'LocationConstraint': 'us-west-1'})
                    self.bucket_cache.add(bucket)

                strm = StringIO.StringIO()
                json.dump(arc, strm, indent=2)
                objpath = objname+'.json'
                self.s3.Object(bucket, objpath).put(Body=strm.getvalue())

                # Add to hash listing - allows us to find entries by hash
                self.s3.Object('marbles-ai-feeds-hash', hash).put(Body=objpath)

            except KeyboardInterrupt:
                # Pass on so we can close the daemon
                raise

            except Exception as e:
                self.logger.error(str(e))
                errors += 1

        # FIXME: better ratelimit method is to randomly spread across all feeds
        time.sleep(1)

    def reload_scraper(self):
        self.scraper = type(self.scraper)()


if __name__ == '__main__':
    usage = 'Usage: %prog [options] [aws-queue-name]'
    parser = OptionParser(usage)
    parser.add_option('-l', '--log-level', type='string', action='store', dest='log_level', help='Logging level')
    parser.add_option('-f', '--log-file', type='string', action='store', dest='log_file', help='Logging file')
    parser.add_option('-D', '--daemonize', action='store_true', dest='daemonize', default=False, help='Run as a daemon.')
    parser.add_option('-R', '--force-read', action='store_true', dest='force_read', default=False, help='Force read.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()
    log_level = options.log_level or 'warning'
    log_file = options.log_file or os.path.join(thisdir, 'newsreader.log')

    main_logger = logging.getLogger('marbles')
    service_logger = logging.getLogger('marbles.service')
    logger = logging.getLogger('marbles.service.newsreader')
    logger.propagate = True # Propagate to parent log

    if not options.daemonize:
        # Log to console
        log_handler = logging.StreamHandler()
    elif len(args) == 0:
        log_handler = logging.FileHandler(log_file, mode='a')
    else:
        # TODO: log to aws
        log_handler = logging.FileHandler(log_file, mode='a')

    log_handler.setLevel(logging.INFO)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)

    if len(args) > 1:
        # TODO: connect to aws simple queue service
        pass

    s3 = boto3.resource('s3')
    archivers = [
        [0, ReaderArchiver(s3, washingtonpost.WPostScraper(), logger, [washingtonpost.WPOST_Politics])],
        [0, ReaderArchiver(s3, nytimes.NYTimesScraper(), logger, [nytimes.NYTIMES_US_Politics])],
        [0, ReaderArchiver(s3, reuters.ReutersScraper(), logger, [reuters.REUTERS_Politics])],
        [0, ReaderArchiver(s3, foxnews.FoxScraper(), logger, [foxnews.FOX_Politics])],
    ]

    ignore_read = not options.force_read
    while True:
        try:
            for arc in archivers:
                if arc[0] > 3:
                    # Stop retrying after 3 errors
                    continue

                try:
                    arc[1].aws_archive(ignore_read)
                    arc[0] = 0      # reset errors
                except KeyboardInterrupt:
                    # Pass on so we can close the daemon
                    raise
                except Exception as e:
                    arc[0] += 1     # count errors
                    logger.error(str(e))

        except KeyboardInterrupt:
            break

        time.sleep(60*10)       # 10 minutes
        for arc in archivers:
            arc.refresh()
        ignore_read = True

    logger.removeHandler(log_handler)


