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
import watchtower
import requests
import base64
import daemon
import signal
import lockfile


# Modify python path if in development mode
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.dirname(os.path.dirname(thisdir))
if os.path.exists(os.path.join(srcdir, 'marbles', 'ie')):
    sys.path.insert(0, srcdir)
terminate = False


from marbles import newsfeed as nf


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


class NewsSource(object):
    """A news source consists of a scraper and a list of feeds."""
    
    def __init__(self, scraper, feed_urls=None):
        self.scraper = scraper
        feed_urls = feed_urls if feed_urls is not None else scraper.get_rss_feed_list()
        self.feeds = [nf.scraper.RssFeed(u) for u in feed_urls]


class ReaderArchiver(object):
    """RSS/Atom reader archive service."""

    def __init__(self, aws, sources, logger, browser, rlimit=0):
        self.browser = browser
        self.aws = aws
        self.sources = sources
        self.bucket_cache = set()
        self.hash_cache = {}
        self.error_cache = {}
        self.logger = logger
        self.rlimit = rlimit

    def close(self):
        self.browser.close()

    def check_bucket_exists(self, bucket):
        if bucket in self.bucket_cache:
            return True
        # Bucket count never exceeds a few 100
        # Refresh all so we handle deletions
        self.bucket_cache = set()
        for bkt in self.aws.s3.buckets.all():
            self.bucket_cache.add(bkt.name)
        return bucket in self.bucket_cache

    def check_hash_exists(self, hash):
        if hash in self.hash_cache:
            return True
        return 0 != len([x for x in self.aws.s3.Bucket('marbles-ai-feeds-hash').objects.filter(Prefix=hash)])

    def clear_bucket_cache(self):
        self.bucket_cache = set()

    def retire_hash_cache(self, limit):
        """Retire least recently used in hash cache."""
        if limit <= len(self.hash_cache):
            return
        # Each value is a timestamp floating point
        vk_sort = sorted(self.hash_cache.items(), key=lambda x: x[1])
        vk_sort.reverse()
        self.hash_cache = dict(iterable=vk_sort[0:(limit>>1)])

    def retire_error_cache(self, limit):
        """Retire least recently used in error cache."""
        if limit <= len(self.error_cache):
            return
        # Each value is a timestamp floating point
        vk_sort = sorted(self.error_cache.items(), key=lambda x: x[1])
        vk_sort.reverse()
        self.error_cache = dict(iterable=vk_sort[0:(limit>>1)])

    def refresh(self):
        global terminate
        if terminate:
            return
        # TODO: Interleave work
        for src in self.sources:
            if terminate:
                return
            for rss in src.feeds:
                if terminate:
                    return
                rss.refresh()
                wait(1)

    def read_all(self, ignore_read):
        global terminate
        for src in self.sources:
            self.read_from_source(src, ignore_read)
            if terminate:
                return
        self.browser.get_blank()

    def read_from_source(self, src, ignore_read):
        global terminate
        if terminate:
            return
        articles = []
        for rss in src.feeds:
            articles.extend(rss.get_articles(ignore_read=ignore_read)) # Returns unread articles

        errors = 0
        for a in articles:
            if terminate:
                return
            try:
                arc = a.archive(src.scraper)
                bucket, objname = a.get_aws_s3_names(arc['content'])
                hash = objname.split('/')[-1]
                self.logger.debug(hash + ' - ' + arc['title'])
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

                # Update hash cache
                self.hash_cache[hash] = time.time()

            except KeyboardInterrupt:
                # Pass on so we can close the daemon
                raise

            except Exception as e:
                # Rate limit errors to the same article id. This avoids flooding the log files.
                if self.rlimit > 0:
                    tmnew = time.time()
                    tmold = self.error_cache.setdefault(a.entry.id, tmnew)
                    if (tmnew - tmold) >= self.rlimit:
                        self.error_cache[a.entry.id] = tmnew
                        self.logger.exception('Exception caught', exc_info=e)
                else:
                    self.logger.exception('Exception caught', exc_info=e)

                errors += 1

            wait(1)


hup_recv = 0
def hup_handler(signum, frame):
    """Forces code to re-read all active articles. This will re-queue articles on AWS SQS."""
    global hup_recv
    hup_recv += 1
    logger.info('SIGHUP')


def term_handler(signum, frame):
    global terminate, logger
    terminate = True
    logger.info('SIGTERM')


def alarm_handler(signum, frame):
    pass


def wait(secs):
    global terminate
    logger.debug('Pausing for %s seconds', secs)
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(secs)
    if not terminate:
        # FIXME: We have a race condition here. If SIGTERM arrives just before the pause call we miss it for secs.
        # A second SIGTERM will help
        signal.pause()
    logger.debug('Continue')


def run_daemon(archivers, logger):
    global hup_recv, terminate
    count = 0
    while not terminate:
        # A HUP will force a read of all articles. Save to local to avoid race condition
        # between test and set
        hup_recv_local = hup_recv
        ignore_read = hup_recv_local == count   # test
        count = hup_recv_local                  # set

        if not ignore_read:
            logger.info('HUP received, refreshing all articles')
            # Clearing will force rebuild of caches
            for arc in archivers:
                arc.retire_error_cache(0)   # clears error cache
                arc.retire_hash_cache(0)    # clears hash cache
                arc.clear_bucket_cache()

        for arc in archivers:
            arc.read_all(ignore_read)
            arc.retire_error_cache(4096)
            arc.retire_hash_cache(4096)
            if terminate:
                break

        # Check every 5 minutes
        wait(5*60)
        # Refresh RSS feeds
        for arc in archivers:
            arc.refresh()
    logger.info('TERM received, exited daemon run loop')


def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)
    # Make some attempt to comply with RFC5424
    log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                               datefmt='%Y-%m-%dT%H:%M:%S%z'))

def init_archivers(queue_name, logger):
    # If we run multiple theads then each thread needs its own AWS resources (S3, SQS etc).
    aws = AWSResources(queue_name)
    # Browser creates a single process for this archive
    browser = nf.scraper.Browser()
    sources = [
        NewsSource(nf.washingtonpost.WPostScraper(browser), [nf.washingtonpost.WPOST_Politics]),
        NewsSource(nf.nytimes.NYTimesScraper(browser), [nf.nytimes.NYTIMES_US_Politics]),
        NewsSource(nf.reuters.ReutersScraper(browser), [nf.reuters.REUTERS_Politics]),
        NewsSource(nf.foxnews.FoxScraper(browser), [nf.foxnews.FOX_Politics]),
    ]

    logger.info('Initialization complete')
    return [
        ReaderArchiver(aws, sources, logger, browser),
    ]


if __name__ == '__main__':
    usage = 'Usage: %prog [options] [aws-queue-name]'
    parser = OptionParser(usage)
    parser.add_option('-l', '--log-level', type='string', action='store', dest='log_level',
                      help='Logging level, defaults to \"info\"')
    parser.add_option('-f', '--log-file', type='string', action='store', dest='log_file',
                      help='Logging file, defaults to console or AWS CloudWatch when running as a daemon.')
    parser.add_option('-d', '--daemonize', action='store_true', dest='daemonize', default=False,
                      help='Run as a daemon. Ignored with -X option.')
    parser.add_option('-r', '--rundir', type='string', action='store', dest='rundir',
                      help='Run directory')
    parser.add_option('-R', '--force-read', action='store_true', dest='force_read', default=False,
                      help='Force read.')
    parser.add_option('-X', '--one-shot', action='store_true', dest='oneshot', default=False,
                      help='Exit after first sync completes.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()

    # Setup logging
    svc_name = os.path.splitext(os.path.basename(__file__))[0]
    log_level=getattr(logging, options.log_level.upper()) if options.log_level else logging.INFO
    logger = logging.getLogger('service.' + svc_name)
    logger.setLevel(log_level)

    console_handler = None
    if options.log_file:
        log_handler = logging.FileHandler(options.log_file, mode='a')
    else:
        if not options.daemonize:
            console_handler = logging.StreamHandler()   # Log to console
            init_log_handler(console_handler, log_level)
            logger.addHandler(console_handler)
        log_handler = watchtower.CloudWatchLogHandler(log_group='core-nlp-services',
                                                      use_queues=False, # Does not shutdown if True
                                                      create_log_group=False)
    init_log_handler(log_handler, log_level)
    logger.addHandler(log_handler)
    queue_name = args[0] if len(args) != 0 else None
    archivers = []

    rundir = os.path.abspath(options.rundir or os.path.join(thisdir, 'run'))
    if options.daemonize:
        if not os.path.exists(rundir):
            os.makedirs(rundir, 0o777)
        if not os.path.isdir(rundir):
            print('%s is not a directory' % rundir)
            sys.exit(1)
        print('Starting service')
        logger.info('Service started')
        context = daemon.DaemonContext(working_directory=thisdir,
                                       umask=0o022,
                                       pidfile=lockfile.FileLock(os.path.join(rundir, svc_name)),
                                       signal_map = {
                                           signal.SIGTERM: term_handler,
                                           signal.SIGHUP:  hup_handler,
                                           signal.SIGALRM: alarm_handler,
                                       })

        hup_recv = 1 if options.force_read else 0
        try:
            with context:
                with open(os.path.join(rundir, svc_name + '.pid'), 'w') as fd:
                    fd.write(str(os.getpid()))
                # When running as a daemon delay creation of headless browsers else they will
                # be parented to the console. Also if we change uid or gid then the browsers
                # start under the same credentials.
                archivers = init_archivers(queue_name, logger)
                if options.oneshot:
                    # Useful for testing
                    for arc in archivers:
                        arc.read_all(not options.force_read)
                else:
                    run_daemon(archivers, logger)

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

    elif not options.oneshot:
        logger.info('Service started')
        archivers = init_archivers(queue_name, logger)
        try:
            ignore_read = not options.force_read
            while True:
                for arc in archivers:
                    arc.read_all(ignore_read)
                ignore_read = True
        except KeyboardInterrupt:
            pass
    else:
        logger.info('Service started')
        archivers = init_archivers(queue_name, logger)
        for arc in archivers:
            arc.read_all(not options.force_read)

    logger.info('Closing headless browsers')
    try:
        for arc in archivers:
            arc.close()
    except Exception as e:
        logger.exception('Exception caught', exc_info=e)

    logger.info('Service stopped')
    logging.shutdown()
    if options.daemonize:
        try:
            os.remove(os.path.join(rundir, svc_name + '.pid'))
        except:
            pass



