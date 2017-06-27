#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import os
import signal
import sys
from optparse import OptionParser

import daemon.pidfile
import grpc
import regex as re  # Has better support for unicode
import requests
import watchtower
from concurrent import futures
from google.protobuf import empty_pb2

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


from marbles.ie import grpc as gsvc
from marbles.ie.grpc import infox_service_pb2
from marbles.log import ExceptionRateLimitedLogAdaptor, set_log_format


# r'\p{P}' is too broad
_UPUNCT = re.compile(r'([,:;\u00a1\u00a7\u00b6\u00b7\u00bf])', re.UNICODE)
_UDQUOTE = re.compile(r'["\u2033\u2034\u2036\u2037\u201c\u201d]', re.UNICODE)
_USQUOTE = re.compile(r"\u2032([^\u2032\u2035]+)\u2035", re.UNICODE)


class InfoxService(infox_service_pb2.InfoxServiceServicer):
    """The service definition"""

    def __init__(self, ccg_stub, state):
        self.ccg_stub = ccg_stub
        self.state = state

    @property
    def logger(self):
        return self.state.logger

    def parse(self, request, context):
        global _USQUOTE, _UDQUOTE, _UPUNCT
        """Parse a message."""
        retry = 3
        while retry:
            if self.state.terminate:
                context.set_code(grpc.StatusCode.CANCELLED)
                context.set_details('Application terminating.')
                raise RuntimeError('Application terminating!')

            try:
                # EasyXXX does not handle these
                smod = _USQUOTE.sub(r" ' \1 ' ", request.text).replace('\u2019', "'")
                smod = _UDQUOTE.sub(r' " ', smod)
                smod = _UPUNCT.sub(r' \1 ', smod)
                ccgbank = gsvc.ccg_parse(self.ccg_stub, smod, gsvc.DEFAULT_SESSION)
                pt = parse_ccg_derivation(ccgbank)
                ccg = process_ccg_pt(pt, options=request.options)
                sent = ccg.get_verbnet_sentence()

                response = infox_service_pb2.GSentence()
                for lex in sent:
                    glex = response.lexemes.add()
                    glex.head = lex.head
                    glex.idx =lex.idx
                    glex.mask = lex.mask
                    for r in lex.refs:
                        glex.refs.append(r.var.to_string())
                    glex.pos = lex.pos.tag
                    glex.word = lex.word
                    glex.stem = lex.stem
                    glex.category = lex.category.signature
                    if lex.wiki_data is not None:
                        glex.wikidata.title = lex.wiki_data.title
                        glex.wikidata.summary = lex.wiki_data.summary
                        glex.wikidata.page_categories.extend(lex.wiki_data.page_categories)
                        glex.wikidata.url = lex.wiki_data.url

                for c in ccg.constituents:
                    gc = response.constituents.add()
                    gc.span.extend(c.span.get_indexes())
                    gc.vntype = c.vntype.signature
                    gc.head = c.chead

                return response

            except requests.exceptions.ConnectionError as e:
                self.state.wait(0.25)
                retry -= 1
                self.logger.exception('Infox.parse', exc_info=e)
                context.set_code(grpc.StatusCode.ABORTED)
                context.set_details(e.message)
                raise

            except Exception as e:
                retry = 0
                self.logger.exception('Infox.parse', exc_info=e)
                context.set_code(grpc.StatusCode.ABORTED)
                context.set_details(e.message)
                raise

        context.set_code(grpc.StatusCode.ABORTED)
        context.set_details('Too many retries!')
        raise RuntimeError('Too many retries!')

    def ping(self, request, context):
        """Does nothing."""
        return empty_pb2.Empty()


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


def start_server(svc_handler, port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    infox_service_pb2.add_InfoxServiceServicer_to_server(svc_handler, server)
    server.add_insecure_port('[::]:%d' % port)
    server.start()
    return server


def run_daemon(server, state):
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

        state.wait(5*60)    # Wait 5 mins

    logger.info('TERM received, exited daemon run loop')
    evt = server.stop(3)
    evt.wait()


def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)
    set_log_format(log_handler)


#-jar $ESRLPATH/build/libs/easysrl-$VERSION-standalone.jar --model $ESRLPATH/model/text
if __name__ == '__main__':
    usage = 'Usage: %prog [options]'
    parser = OptionParser(usage)
    parser.add_option('-l', '--log-level', type='string', action='store', dest='log_level',
                      help='Logging level, defaults to \"info\"')
    parser.add_option('-f', '--log-file', type='string', action='store', dest='log_file',
                      help='Logging file, defaults to console or AWS CloudWatch when running as a daemon.')
    parser.add_option('-d', '--daemonize', action='store_true', dest='daemonize', default=False,
                      help='Run as a daemon.')
    parser.add_option('-g', '--grpc-daemon', type='string', action='store', dest='grpc_daemon',
                      help='gRPC parser daemon name, [easysrl (default),easyccg]')
    parser.add_option('-p', '--pid-file', type='string', action='store', dest='pid_file',
                      help='PID lock file, defaults to directory containing daemon.')
    parser.add_option('-P', '--port', type='int', action='store', dest='port', default=gsvc.INFOX_PORT,
                      help='Port to accept connection, defaults to %d.' % gsvc.INFOX_PORT)
    parser.add_option('-j', '--jar', type='string', action='store', dest='jar_file',
                      help='Jar file. Must be combined with -m.')
    parser.add_option('-m', '--model', type='string', action='store', dest='model_dir',
                      help='Model folder. Must be combined with -m.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')

    (options, args) = parser.parse_args()
    # Delay import so help is displayed quickly without loading model.
    from marbles.aws import ServiceState
    from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
    from marbles.ie.semantics.ccg import process_ccg_pt


    class IxServiceState(ServiceState):
        def __init__(self, *args, **kwargs):
            super(IxServiceState, self).__init__(*args, **kwargs)

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
    state = IxServiceState(logger)

    if options.pid_file is None:
        rundir = os.path.join(thisdir, 'run')
        pid_file = os.path.join(rundir, svc_name + '.pid')
    else:
        pid_file = os.path.abspath(options.pid_file)
        rundir = os.path.dirname(pid_file)

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

    if options.daemonize:
        if not os.path.exists(rundir):
            os.makedirs(rundir, 0o777)
        if not os.path.isdir(rundir):
            print('%s is not a directory' % rundir)
            sys.exit(1)
        print('Starting service')
        context = daemon.DaemonContext(working_directory=thisdir,
                                       umask=0o022,
                                       pidfile=daemon.pidfile.PIDLockFile(pid_file),
                                       signal_map = {
                                           signal.SIGTERM: term_handler,
                                           signal.SIGHUP:  hup_handler,
                                           signal.SIGALRM: alarm_handler,
                                       })

        server = None
        try:
            grpc_daemon = gsvc.CcgParserService(grpc_daemon_name,
                                                logger=logger,
                                                workdir=thisdir,
                                                modeldir=model_dir,
                                                jarfile=jar_file)
            svc_handler = InfoxService(grpc_daemon.open_client(), state)
            server = start_server(svc_handler, options.port)
            with context:
                logger.info('Service started')
                with open(os.path.join(rundir, svc_name + '.pid'), 'w') as fd:
                    fd.write(str(os.getpid()))
                run_daemon(server, state)

        except Exception as e:
            if not server:
                print('An error occured starting service')
            else:
                server.stop(0)
            logger.exception('Exception caught', exc_info=e)

    else:
        try:
            grpc_daemon = gsvc.CcgParserService(daemon=grpc_daemon_name,
                                                logger=logger,
                                                workdir=thisdir,
                                                modeldir=model_dir,
                                                jarfile=jar_file)
            svc_handler = InfoxService(grpc_daemon.open_client(), state)
            server = start_server(svc_handler, options.port)
            logger.info('Service started')
            run_daemon(server, state)

        except KeyboardInterrupt:
            evt = server.stop(3)
            evt.wait()

        except Exception as e:
            logger.exception('Exception caught', exc_info=e)
            server.stop(0)

    try:
        if grpc_daemon is not None:
            grpc_daemon.shutdown()
    except Exception as e:
        logger.exception('Exception caught', exc_info=e)

    logger.info('Service stopped')
    logging.shutdown()
    if options.daemonize:
        try:
            os.remove(pid_file)
        except:
            pass
