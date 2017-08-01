#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
from optparse import OptionParser
from logging import getLevelName


# Modify python path if in development mode
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.dirname(os.path.dirname(thisdir))
if os.path.exists(os.path.join(srcdir, 'marbles', 'ie')):
    sys.path.insert(0, srcdir)
    projdir = os.path.dirname(os.path.dirname(srcdir))
else:
    # Only set when in devel tree
    projdir = None


from marbles.ie import grpc
from marbles.aws import svc


class CcgParserExecutor(svc.ServiceExecutor):

    def __init__(self, state, news_queue_name, ccg_queue_name, grpc_daemon_name, jar_file, extra_args):
        super(CcgParserExecutor, self).__init__(wakeup=5*60, state_or_logger=state)
        self.grpc_daemon_name = grpc_daemon_name
        self.grpc_daemon = None
        self.parsers = None
        self.news_queue_name = news_queue_name
        self.ccg_queue_name = ccg_queue_name
        self.extra_args = extra_args
        self.jar_file = jar_file

    def on_start(self, workdir):
        # Start dependent gRPC CCG parser service
        self.grpc_daemon = grpc.CcgParserService(self.grpc_daemon_name,
                                                 workdir=workdir,
                                                 extra_args=self.extra_args,
                                                 jarfile=self.jar_file)
        # If we run multiple threads then each thread needs its own resources (S3, SQS etc).
        res = AwsNewsQueueReaderResources(self.grpc_daemon.open_client(), news_queue_name, ccg_queue_name)
        self.parsers = [
            AwsNewsQueueReader(res, state, CO_NO_WIKI_SEARCH)
        ]

    def on_term(self, graceful):
        pass

    def on_shutdown(self):
        if self.grpc_daemon is not None:
            self.grpc_daemon.shutdown()
            self.logger.info('gRPC ccg parser service stopped')

    def on_wake(self):
        """Called regularly in run loop"""
        for ccgp in self.parsers:
            ccgp.run()


#-jar $ESRLPATH/build/libs/easysrl-$VERSION-standalone.jar --model $ESRLPATH/model/text
if __name__ == '__main__':
    usage = 'Usage: %prog [options] [news-queue-name [ccg-queue-name]] '
    parser = OptionParser(usage)
    parser.add_option('-g', '--grpc-daemon', type='string', action='store', dest='grpc_daemon',
                      help='gRPC parser daemon name, [easysrl (default), neuralccg]')
    parser.add_option('-j', '--jar', type='string', action='store', dest='jar_file',
                      help='Jar file. Must be combined with -m.')
    parser.add_option('-m', '--model', type='string', action='store', dest='model_dir',
                      help='Model folder. Must be combined with -m.')
    svc.init_parser_options(parser)

    (options, args) = parser.parse_args()
    # Delay import so help is displayed quickly without loading model.
    from marbles.aws import AwsNewsQueueReaderResources, AwsNewsQueueReader
    from marbles.ie.core.constants import CO_NO_WIKI_SEARCH

    grpc_daemon_name = options.grpc_daemon or 'easysrl'
    if ':' in grpc_daemon_name:
        gargs = grpc_daemon_name.split(':')
        grpc_daemon_name = gargs[0]
        gargs = gargs[1:]
    else:
        gargs = []
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
    stream_name = 'svc-' + svc_name
    state = svc.process_parser_options(options, svc_name, stream_name)

    model_dir = None
    jar_file = None
    if options.model_dir is not None and options.jar_file is not None:
        jar_file = os.path.abspath(options.jar_file)
        model_dir = os.path.abspath(options.model_dir)
        if not os.path.isdir(model_dir):
            print('%s is not a directory' % model_dir)
            sys.exit(1)
        elif not os.path.isfile(jar_file):
            print('%s is not a file' % jar_file)
            sys.exit(1)
    elif options.model_dir is not None or options.jar_file is not None:
        print('-j|--jar option must be combined with -m|--model option')
        sys.exit(1)

    gargs.extend(['-m', model_dir, '-A', stream_name, '-l', getLevelName(state.root_logger.level)])
    svc = CcgParserExecutor(state, news_queue_name=news_queue_name, ccg_queue_name=ccg_queue_name,
                            grpc_daemon_name=grpc_daemon_name, jar_file=jar_file,
                            extra_args=gargs)
    svc.run(thisdir)
