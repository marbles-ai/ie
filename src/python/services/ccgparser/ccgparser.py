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
from marbles.log import ExceptionRateLimitedLogAdaptor


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


def run_daemon(parsers, state):
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

        state.wait(5*60)    # Wait 5 mins

    logger.info('TERM received, exited daemon run loop')


def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)
    # Make some attempt to comply with RFC5424
    log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                               datefmt='%Y-%m-%dT%H:%M:%S%z'))

def init_service(grpc_daemon, news_queue_name, ccg_queue_name, state):
    # If we run multiple threads then each thread needs its own resources (S3, SQS etc).
    res = AwsNewsQueueReaderResources(grpc_daemon.open_client(), news_queue_name, ccg_queue_name)
    return [
        AwsNewsQueueReader(res, state, CO_NO_WIKI_SEARCH)
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
    parser.add_option('-g', '--grpc-daemon', type='string', action='store', dest='grpc_daemon',
                      help='gRPC daemon name, [easysrl (default),easyccg]')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()
    # Delay import so help is displayed quickly without loading model.
    from marbles.aws import AwsNewsQueueReaderResources, AwsNewsQueueReader, ServiceState
    from marbles.ie.compose import CO_NO_WIKI_SEARCH


    class NRServiceState(ServiceState):
        def __init__(self, *args, **kwargs):
            super(NRServiceState, self).__init__(*args, **kwargs)

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


    grpc_daemon_name = options.grpc_daemon or 'easysrl'
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
    grpc_daemon = None
    state = NRServiceState(logger)

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
            grpc_daemon = grpc.CcgParserService(grpc_daemon_name, logger=logger, workdir=thisdir)
            parsers = init_service(grpc_daemon, news_queue_name, ccg_queue_name, state)
            with context:
                logger.info('Service started')
                with open(os.path.join(rundir, svc_name + '.pid'), 'w') as fd:
                    fd.write(str(os.getpid()))
                run_daemon(parsers, state)

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

    else:
        try:
            grpc_daemon = grpc.CcgParserService(daemon=grpc_daemon_name, logger=logger, workdir=thisdir)
            parsers = init_service(grpc_daemon, news_queue_name, ccg_queue_name, state)
            logger.info('Service started')
            while True:
                for ccg in parsers:
                    ccg.run()

        except KeyboardInterrupt:
            pass

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

    try:
        if grpc_daemon is not None:
            grpc_daemon.shutdown()
    except Exception as e:
        logger.exception('Exception caught', exc_info=e)

    logger.info('Service stopped')
    logging.shutdown()
    if options.daemonize:
        try:
            os.remove(os.path.join(rundir, svc_name + '.pid'))
        except:
            pass
