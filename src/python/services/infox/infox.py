#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
from optparse import OptionParser
import grpc
import requests
from concurrent import futures
from google.protobuf import empty_pb2
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


from marbles.ie import grpc as gsvc
from marbles.ie.grpc import infox_service_pb2
from marbles.aws import svc


class InfoxService(infox_service_pb2.InfoxServiceServicer):
    """The service definition"""

    def __init__(self, ccg_stub, state):
        self.ccg_stub = ccg_stub
        self.state = state

    @property
    def logger(self):
        return self.state.logger

    def parse(self, request, context):
        """Parse a message."""
        retry = 3
        while retry:
            if self.state.terminate:
                context.set_code(grpc.StatusCode.CANCELLED)
                context.set_details('Application terminating.')
                raise RuntimeError('Application terminating!')

            try:
                # EasyXXX does not handle these
                smod = preprocess_sentence(request.text)
                ccgbank = gsvc.ccg_parse(self.ccg_stub, smod, gsvc.DEFAULT_SESSION)
                pt = parse_ccg_derivation(ccgbank)
                sent = process_ccg_pt(pt, options=request.options)

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

                for c in sent.constituents:
                    gc = response.constituents.add()
                    # TODO: rename - its not a span
                    gc.span.extend(c.lex_range)
                    gc.span.append(c.dhead)
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


class InfoxExecutor(svc.ServiceExecutor):

    def __init__(self, state, grpc_daemon_name, jar_file, extra_args, port=None):
        super(InfoxExecutor, self).__init__(wakeup=5*60, state_or_logger=state)
        self.grpc_daemon_name = grpc_daemon_name
        self.grpc_daemon = None
        self.extra_args = extra_args
        self.jar_file = jar_file
        self.server = None
        # TODO: get port from extra_args else use default port
        self.port = port

    def on_start(self, workdir):
        # Start dependent gRPC CCG parser service
        self.grpc_daemon = gsvc.CcgParserService(self.grpc_daemon_name,
                                            workdir=workdir,
                                            extra_args=self.extra_args,
                                            jarfile=self.jar_file,
                                            debug=not self.state.daemonize)
        # Start InfoX gRPC service
        svc_handler = InfoxService(self.grpc_daemon.open_client(), self.state)
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        infox_service_pb2.add_InfoxServiceServicer_to_server(svc_handler, self.server)
        self.server.add_insecure_port('[::]:%d' % self.port)
        self.server.start()

    def on_term(self, graceful):
        if self.server is not None:
            if graceful:
                self.logger.debug('Graceful shutdown of gRPC main service')
                evt = self.server.stop(3)
                evt.wait(3)
            else:
                self.logger.debug('Immediate shutdown of gRPC main service')
                self.server.stop(0)
            self.logger.info('gRPC main service stopped')


#-jar $ESRLPATH/build/libs/easysrl-$VERSION-standalone.jar --model $ESRLPATH/model/text
if __name__ == '__main__':
    usage = 'Usage: %prog [options]'
    parser = OptionParser(usage)
    parser.add_option('-g', '--grpc-daemon', type='string', action='store', dest='grpc_daemon',
                      help='gRPC parser daemon name, [easysrl (default), neuralccg]')
    parser.add_option('-P', '--port', type='int', action='store', dest='port', default=gsvc.INFOX_PORT,
                      help='Port to accept connection, defaults to %d.' % gsvc.INFOX_PORT)
    parser.add_option('-j', '--jar', type='string', action='store', dest='jar_file',
                      help='Jar file. Must be combined with -m.')
    parser.add_option('-m', '--model', type='string', action='store', dest='model_dir',
                      help='Model folder. Must be combined with -m.')
    svc.init_parser_options(parser)

    (options, args) = parser.parse_args()
    # Delay import so help is displayed quickly without loading model.
    from marbles.ie.ccg import parse_ccg_derivation2 as parse_ccg_derivation
    from marbles.ie.semantics.ccg import process_ccg_pt
    from marbles.ie.utils.text import preprocess_sentence

    grpc_daemon_name = options.grpc_daemon or 'easysrl'
    if ':' in grpc_daemon_name:
        gargs = grpc_daemon_name.split(':')
        grpc_daemon_name = gargs[0]
        gargs = gargs[1:]
    else:
        gargs = []
    svc_name = os.path.splitext(os.path.basename(__file__))[0]
    stream_name = 'svc-' + svc_name
    state = svc.process_parser_options(options, svc_name, stream_name)

    model_dir = None
    jar_file = None
    if options.model_dir is not None and options.jar_file is not None:
        jar_file = os.path.abspath(os.path.expanduser(options.jar_file))
        model_dir = os.path.abspath(os.path.expanduser(options.model_dir))
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
    svc = InfoxExecutor(state, grpc_daemon_name, jar_file, gargs, options.port)
    svc.run(thisdir)
