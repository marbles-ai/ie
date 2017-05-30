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
import watchtower
import requests
import base64


# Modify python path if in development mode
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.dirname(thisdir)
if os.path.exists(os.path.join(srcdir, 'marbles', 'ie')):
    sys.path.insert(0, srcdir)


from marbles.newsfeed import *


class AWSResources:
    """AWS resources."""

    def __init__(self, queue_name=None):
        self.s3 = boto3.resource('s3')
        if queue_name:
            self.sqs = boto3.client('sqs')
            if queue_name == 'default-queue':
                resp = self.sqs.get_queue_url(QueueName='marbles-ai-rss-aggregator')
            else:
                resp = self.sqs.get_queue_url(QueueName=queue_name)
            self.queue_url = resp['QueueUrl']
        else:
            self.sqs = None
            self.queue_url = None


class ReaderArchiver(object):
    """RSS/Atom reader archive service."""

    def __init__(self, aws, scrape, logger, feed_urls=None):
        self.aws = aws
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
        for bkt in self.aws.s3.buckets.all():
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
                exists = 0 != len([x for x in self.aws.s3.Bucket('marbles-ai-feeds-hash').objects.filter(Prefix=hash)])
                if exists:
                    continue

                if not self.check_bucket_exists(bucket):
                    # Create a bucket
                    self.aws.s3.create_bucket(Bucket=bucket,
                                          CreateBucketConfiguration={'LocationConstraint': 'us-west-1'})
                    self.bucket_cache.add(bucket)

                strm = StringIO.StringIO()
                json.dump(arc, strm, indent=2)
                objpath = objname+'.json'
                data = strm.getvalue()
                self.aws.s3.Object(bucket, objpath).put(Body=data)

                # Add to hash listing - allows us to find entries by hash
                self.aws.s3.Object('marbles-ai-feeds-hash', hash).put(Body=objpath)

                # Add to AWS processing queue
                if self.aws.sqs:
                    attributes = {
                        's3': {
                            'DataType': 'String',
                            'StringValue': bucket + '/' + objname
                        },
                        'hash': {
                            'DataType': 'String',
                            'StringValue': hash
                        }
                    }
                    # Store thumbnail in message so website has immediate access
                    d = arc.setdefault('media', {})
                    if d.setdefault('thumbnail', -1) >= 0:
                        media = d['content'][ d['thumbnail']]
                        r = requests.get(media['url'])
                        attributes['media_thumbnail'] = {
                            'DataType': 'String',
                            'StringValue': base64.b64encode(r.content)
                        }
                        attributes['media_type'] = {
                            'DataType': 'String',
                            'StringValue': media['type']
                        }
                    # Send the message to our queue
                    response = self.aws.sqs.send_message(QueueUrl=self.aws.queue_url, DelaySeconds=0,
                                                     MessageAttributes=attributes, MessageBody=data)
                    # TODO: make level debug once its working
                    self.logger.info('Sent msg(%s) -> s3(%s)', response['MessageId'], hash)


            except KeyboardInterrupt:
                # Pass on so we can close the daemon
                raise

            except Exception as e:
                self.logger.exception('Exception caught', exc_info=e)
                errors += 1

        # FIXME: better ratelimit method is to randomly spread across all feeds
        self.scrape.get_blank()
        time.sleep(1)

    def reload_scraper(self):
        self.scraper = type(self.scraper)()


if __name__ == '__main__':
    usage = 'Usage: %prog [options] [aws-queue-name]'
    parser = OptionParser(usage)
    parser.add_option('-l', '--log-level', type='string', action='store', dest='log_level',
                      help='Logging level, defaults to \"info\"')
    parser.add_option('-f', '--log-file', type='string', action='store', dest='log_file',
                      help='Logging file, defaults to AWS CloudWatch.')
    parser.add_option('-D', '--daemonize', action='store_true', dest='daemonize', default=False,
                      help='Run as a daemon.')
    parser.add_option('-R', '--force-read', action='store_true', dest='force_read', default=False,
                      help='Force read.')
    parser.add_option('-X', '--exit-early', action='store_true', dest='exit_early', default=False,
                      help='Exit after first sync completes.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()

    # Setup logging
    log_level=getattr(logging, options.log_level.upper()) if options.log_level else logging.INFO
    logger = logging.getLogger('service.' + os.path.splitext(os.path.basename(__file__))[0])
    logger.setLevel(log_level)

    if options.log_file:
        log_handler = logging.FileHandler(options.log_file, mode='a')
    elif not options.daemonize:
        log_handler = logging.StreamHandler()   # Log to console
    else:   # Log to aws
        log_handler = watchtower.CloudWatchLogHandler()

    log_handler.setLevel(log_level)
    # Make some attempt to comply with RFC5424
    log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                               datefmt='%Y-%m-%dT%H:%M:%S%z'))
    logger.addHandler(log_handler)

    logger.info('Service started')

    # If we run multiple theads then each thread needs its own AWS resources (S3, SQS etc).
    aws = AWSResources(args[0] if len(args) != 0 else None)
    archivers = [
        [0, ReaderArchiver(aws, washingtonpost.WPostScraper(), logger, [washingtonpost.WPOST_Politics])],
        [0, ReaderArchiver(aws, nytimes.NYTimesScraper(), logger, [nytimes.NYTIMES_US_Politics])],
        [0, ReaderArchiver(aws, reuters.ReutersScraper(), logger, [reuters.REUTERS_Politics])],
        [0, ReaderArchiver(aws, foxnews.FoxScraper(), logger, [foxnews.FOX_Politics])],
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

            if options.exit_early:
                break

            time.sleep(60*10)       # 10 minutes
            for arc in archivers:
                arc[1].refresh()

        except KeyboardInterrupt:
            logger.info('Exiting due to KeyboardInterrupt')
            break

        ignore_read = True

    logger.info('Service stopped')
    #logger.removeHandler(log_handler)


