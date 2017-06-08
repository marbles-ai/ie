#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
import logging
from optparse import OptionParser
import boto3
import time
import watchtower
import requests
import daemon
import signal
import lockfile
from nltk.tokenize import sent_tokenize


# Modify python path if in development mode
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.dirname(os.path.dirname(thisdir))
if os.path.exists(os.path.join(srcdir, 'marbles', 'ie')):
    sys.path.insert(0, srcdir)
    projdir = os.path.dirname(os.path.dirname(srcdir))
else:
    # Only set when in devel tree
    projdir = None
terminate = False


from marbles.ie import grpc
from marbles.ie import grpc
from marbles.log import ExceptionRateLimitedLogAdaptor



class Resources:
    """AWS and gRPC resources."""

    def __init__(self, stub, news_queue_name, ccg_queue_name=None):
        global projdir, thisdir
        self.s3 = boto3.resource('s3')
        self.sqs = boto3.resource('sqs')
        self.stub = stub
        if news_queue_name == 'default-queue':
            resp = self.sqs.get_queue_by_name(QueueName='marbles-ai-rss-aggregator')
        else:
            resp = self.sqs.get_queue_by_name(QueueName=news_queue_name)
        self.news_queue = resp

        if ccg_queue_name:
            if ccg_queue_name == 'default-queue':
                resp = self.sqs.get_queue_by_name(QueueName='marbles-ai-discourse-logic')
            else:
                resp = self.sqs.get_queue_by_name(QueueName=ccg_queue_name)
            self.ccg_queue = resp
        else:
            self.ccg_queue = None


class CcgParser(object):
    """CCG Parser handler"""

    def __init__(self, res, logger):
        self.res = res
        self.logger = logger

    def run(self):
        # Process messages by printing out body and optional author name
        for message in self.res.news_queue.receive_messages(MessageAttributeNames=['All']):
            # Attributes will be passed onto next queue
            attributes = message.message_attributes
            body = message.body
            retry = 3
            ccgbank = None
            title = body['title']
            paragraphs_in = filter(lambda y: len(y) != 0, map(lambda x: x.strip(), body['content'].split('\n')))
            paragraphs_out = []
            for p in paragraphs_in:
                sentences = filter(lambda x: len(x.strip()) != 0, sent_tokenize(p))
                paragraphs_out.append(sentences)

            result = {}
            while retry:
                try:
                    ccgbank = grpc.ccg_parse(self.res.stub, title, grpc.DEFAULT_SESSION)
                    pt = parse_ccg_derivation(ccgbank)
                    ccg = process_ccg_pt(pt)
                    result['title']['lexemes'] = [x.get_json() for x in ccg.get_span()]
                    result['title']['constituents'] = [c.get_json() for c in ccg.constituents]
                    ccgpara = []
                    result['paragraphs'] = ccgpara
                    for sentences in paragraphs_out:
                        ccgsent = []
                        ccgpara.append(ccgsent)
                        for s in sentences:
                            ccgbank = grpc.ccg_parse(self.res.stub, s, grpc.DEFAULT_SESSION)
                            pt = parse_ccg_derivation(ccgbank)
                            ccg = process_ccg_pt(pt)
                            ccgentry = {}
                            ccgentry['lexemes'] = [x.get_json() for x in ccg.get_span()]
                            ccgentry['constituents'] = [c.get_json() for c in ccg.constituents]
                            ccgsent.append(ccgentry)
                    break   # exit while
                except requests.exceptions.ConnectionError as e:
                    time.sleep(0.25)
                    retry -= 1
                    self.logger.exception(exc_info=e)
                except Exception as e:
                    # After X reads AWS sends the item to the dead letter queue.
                    # X is configurable in AWS console.
                    retry = 0
                    self.logger.exception(exc_info=e, rlimitby=attributes['hash'])

            # retry == 0 indicates failure
            if retry == 0:
                continue

            # Let the queue know that the message is processed
            message.delete()
            if self.res.news_queue:
                response = self.res.news_queue(MessageAttributes=attributes,
                                               MessageBody=result)


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


def run_daemon(parsers, logger):
    global hup_recv, terminate
    count = 0
    while not terminate:
        # A HUP will force a read of all articles. Save to local to avoid race condition
        # between test and set
        hup_recv_local = hup_recv
        hup_signaled = hup_recv_local == count  # test
        count = hup_recv_local                  # set

        if hup_signaled:
            logger.info('HUP received, refreshing')

        for ccg in parsers:
            ccg.run()

    logger.info('TERM received, exited daemon run loop')


def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)
    # Make some attempt to comply with RFC5424
    log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                               datefmt='%Y-%m-%dT%H:%M:%S%z'))

def init_service(ccgdaemon, news_queue_name, ccg_queue_name, logger):
    # If we run multiple threads then each thread needs its own resources (S3, SQS etc).
    res = Resources(ccgdaemon.open_client(), news_queue_name, ccg_queue_name)
    return [
        CcgParser(res, logger)
    ]


if __name__ == '__main__':
    usage = 'Usage: %prog [options] [news-queue-name [ccg-queue-name]] '
    parser = OptionParser(usage)
    parser.add_option('-l', '--log-level', type='string', action='store', dest='log_level',
                      help='Logging level, defaults to \"info\"')
    parser.add_option('-f', '--log-file', type='string', action='store', dest='log_file',
                      help='Logging file, defaults to console or AWS CloudWatch when running as a daemon.')
    parser.add_option('-d', '--daemonize', action='store_true', dest='daemonize', default=False,
                      help='Run as a daemon.')
    parser.add_option('-r', '--rundir', type='string', action='store', dest='rundir',
                      help='Run directory')
    parser.add_option('-d', '--ccg-daemon', type='string', action='store', dest='ccgdaemon',
                      help='CCG daemon name, [easysrl (default),easyccg]')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()
    ccgdaemon_name = options.ccgdaemon or 'easysrl'
    news_queue_name = 'default-queue'
    ccg_queue_name = news_queue_name
    if len(args) == 1:
        news_queue_name = args[0]
        ccg_queue_name = None
    elif len(args) == 2:
        news_queue_name = args[0]
        ccg_queue_name = args[1]
    else:
        parser.print_usage()
        sys.exit(1)

    # Delay imports so help text can be dislayed without loading model
    from marbles.ie.compose import CO_ADD_STATE_PREDICATES, CO_NO_VERBNET, CO_BUILD_STATES
    from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
    from marbles.ie.ccg2drs import process_ccg_pt

    # Setup logging
    svc_name = os.path.splitext(os.path.basename(__file__))[0]
    log_level = getattr(logging, options.log_level.upper()) if options.log_level else logging.INFO
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
    parsers = []
    ccgdaemon = None

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

        try:
            logger.info('Service started')
            ccgdaemon = grpc.CcgParserService(ccgdaemon_name, logger=logger, workdir=thisdir)
            parsers = init_service(ccgdaemon, news_queue_name, ccg_queue_name, logger)
            with context:
                with open(os.path.join(rundir, svc_name + '.pid'), 'w') as fd:
                    fd.write(str(os.getpid()))
                run_daemon(parsers, logger)

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

    else:
        try:
            logger.info('Service started')
            ccgdaemon = grpc.CcgParserService(ccgdaemon_name, logger=logger, workdir=thisdir)
            parsers = init_service(ccgdaemon, news_queue_name, ccg_queue_name, logger)
            while True:
                for ccg in parsers:
                    ccg.run()
                ignore_read = True

        except KeyboardInterrupt:
            pass

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

    try:
        for ccg in parsers:
            pass
        if ccgdaemon:
            ccgdaemon.shutdown()
    except Exception as e:
        logger.exception('Exception caught', exc_info=e)

    logger.info('Service stopped')
    logging.shutdown()
    if options.daemonize:
        try:
            os.remove(os.path.join(rundir, svc_name + '.pid'))
        except:
            pass
