#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
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
from marbles.log import ExceptionRateLimitedLogAdaptor


class NewsSource(object):
    """A news source consists of a scraper and a list of feeds."""
    
    def __init__(self, scraper, feed_urls=None):
        self.scraper = scraper
        feed_urls = feed_urls if feed_urls is not None else scraper.get_rss_feed_list()
        self.feeds = [nf.scraper.RssFeed(u) for u in feed_urls]


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


def run_daemon(archivers, state):
    global hup_recv, terminate
    count = 0
    while not terminate:
        # A HUP will force a read of all articles. Save to local to avoid race condition
        # between test and set
        hup_recv_local = hup_recv
        ignore_read = hup_recv_local == count   # test
        count = hup_recv_local                  # set

        if not ignore_read:
            state.logger.info('HUP received, refreshing all articles')
            # Clearing will force rebuild of caches
            for arc in archivers:
                arc.retire_hash_cache(0)    # clears hash cache
                arc.clear_bucket_cache()

        for arc in archivers:
            arc.read_all(ignore_read)
            # Keep hash cache size in range 4096-8192
            if len(arc.hash_cache) >= 8192:
                arc.retire_hash_cache(4096)
            if terminate:
                break

        # Check every 5 minutes
        state.wait(5*60)
        # Refresh RSS feeds
        for arc in archivers:
            arc.refresh()
    state.logger.info('TERM received, exited daemon run loop')


def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)
    # Make some attempt to comply with RFC5424
    log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                               datefmt='%Y-%m-%dT%H:%M:%S%z'))

def init_archivers(queue_name, state):
    # If we run multiple theads then each thread needs its own AWS resources (S3, SQS etc).
    aws = AwsNewsQueueWriterResources(queue_name)
    # Browser creates a single process for this archive
    browser = nf.scraper.Browser()
    sources = [
        NewsSource(nf.washingtonpost.WPostScraper(browser), [nf.washingtonpost.WPOST_Politics]),
        NewsSource(nf.nytimes.NYTimesScraper(browser), [nf.nytimes.NYTIMES_US_Politics]),
        NewsSource(nf.reuters.ReutersScraper(browser), [nf.reuters.REUTERS_Politics]),
        NewsSource(nf.foxnews.FoxScraper(browser), [nf.foxnews.FOX_Politics]),
    ]

    state.logger.info('Initialization complete')
    return [
        AwsNewsQueueWriter(aws, state, sources, browser),
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

    # Delay import so help is displayed quickly
    from marbles.aws import AwsNewsQueueWriterResources, AwsNewsQueueWriter, ServiceState

    class NWServiceState(ServiceState):
        def __init__(self, *args, **kwargs):
            super(NWServiceState, self).__init__(*args, **kwargs)

        @property
        def terminate(self):
            global terminate
            return terminate

        def wait(self, seconds):
            global terminate
            self.logger.debug('Pausing for %s seconds', seconds)
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(seconds)
            if not terminate:
                # FIXME: We have a race condition here.
                # If SIGTERM arrives just before the pause call we miss it for `seconds`.
                # A second SIGTERM will help
                signal.pause()
            self.logger.debug('Continue')

    # Setup logging
    svc_name = os.path.splitext(os.path.basename(__file__))[0]
    log_level=getattr(logging, options.log_level.upper()) if options.log_level else logging.INFO
    root_logger = logging.getLogger('marbles')
    root_logger.setLevel(log_level)
    actual_logger = logging.getLogger('marbles.svc.' + svc_name)
    logger = ExceptionRateLimitedLogAdaptor(actual_logger)

    console_handler = None
    if options.log_file:
        log_handler = logging.FileHandler(options.log_file, mode='a')
    else:
        if not options.daemonize:
            console_handler = logging.StreamHandler()   # Log to console
            init_log_handler(console_handler, log_level)
            root_logger.addHandler(console_handler)
        log_handler = watchtower.CloudWatchLogHandler(log_group='core-nlp-services',
                                                      use_queues=False, # Does not shutdown if True
                                                      create_log_group=False)
    init_log_handler(log_handler, log_level)
    root_logger.addHandler(log_handler)
    queue_name = args[0] if len(args) != 0 else None
    archivers = []
    state = NWServiceState(logger)

    rundir = os.path.abspath(options.rundir or os.path.join(thisdir, 'run'))
    if options.daemonize:
        if not os.path.exists(rundir):
            os.makedirs(rundir, 0o777)
        if not os.path.isdir(rundir):
            print('%s is not a directory' % rundir)
            sys.exit(1)
        print('Starting service')
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
                logger.info('Service started')
                with open(os.path.join(rundir, svc_name + '.pid'), 'w') as fd:
                    fd.write(str(os.getpid()))
                # When running as a daemon delay creation of headless browsers else they will
                # be parented to the console. Also if we change uid or gid then the browsers
                # start under the same credentials.
                archivers = init_archivers(queue_name, state)
                if options.oneshot:
                    # Useful for testing
                    for arc in archivers:
                        arc.read_all(not options.force_read)
                else:
                    run_daemon(archivers, state)

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

    else:
        logger.info('Service started')
        try:
            archivers = init_archivers(queue_name, state)
            ignore_read = not options.force_read
            while not terminate:
                for arc in archivers:
                    arc.read_all(ignore_read)
                ignore_read = True
                terminate = options.oneshot
        except KeyboardInterrupt:
            pass

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



