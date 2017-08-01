from marbles_service_pb2 import LucidaServiceStub, QueryInput, QuerySpec, Request, Response
from infox_service_pb2 import InfoxServiceStub, GConstituent, GLexeme, GSentence, GText, GWikidata
from google.protobuf import empty_pb2
import grpc
import os
import time
import subprocess
import logging
from marbles import PROJDIR, USE_DEVEL_PATH, safe_utf8_encode, safe_utf8_decode, future_string


_logger = logging.getLogger(__name__)


## EasySRL gRPC service port
EASYSRL_PORT = 8084

## NeuralCCG gRPC service port
NEURALCCG_PORT = 8090

INFOX_PORT = 8086

## Default Session Id
DEFAULT_SESSION='default'

_GRPC_RUNNING = set()


def kill_all_grpc():
    global _GRPC_RUNNING
    # Copy because shutdown removes entries
    running = [x for x in _GRPC_RUNNING]
    for g in running:
        try:
            g.shutdown()
        except:
            pass


def create_query_input(typename, data):
    """Build query input. Typically not required since ccg_parse() does this for you.

    Args:
        typename: A data type string.
        data: The data.
    """
    query_input = QueryInput()
    query_input.type = typename
    query_input.data.append(str(data))
    return query_input


def get_client_transport(host, port):
    """Open a connection to the gRPC service endpoint

    Args:
        host: The host domain name. Set to local_host if running locally.
        port: The service port. Either EASYSRL_PORT or NEURALCCG_PORT.

    Returns:
        A tuple of the client end-point stub and channel
    """
    channel = grpc.insecure_channel('%s:%u' % (host, port))
    stub = LucidaServiceStub(channel)
    return stub, channel


def create_session(client, output_format, session_prefix=None):
    """Create a session supporting the specified output format.

    Args:
        client: The client end-point stub returned from get_client_transport()
        output_format: The output format string. One of: 'ccgbank', 'html', 'logic', or 'extended'.
        session_prefix: Optional session prefix. Defaults to module path.

    Returns:
        The session id string.

    Remarks:
        A default session always exists. Only call this if you want to look at other output formats,
        for example html. This operation can take up to 30 seconds to complete.
    """
    if session_prefix is None:
        session_prefix, _ = os.path.splitext(os.path.basename(__file__))

    if output_format not in ['ccgbank', 'html', 'logic', 'extended']:
        raise ValueError('bad output format passed to create_session - %s' % output_format)

    query_input = create_query_input('text', output_format.upper())
    request = Request()
    request.LUCID = session_prefix.upper() + '-' + output_format
    request.spec.name = 'create'
    request.spec.content.extend([query_input])
    # Don't use synchronous call because it will timeout - client.create(request).
    #
    # Call create asynchronously.
    create_future = client.create.future(request, 60)
    # FIXME: Need to add error reporting to Response structure.
    notused = create_future.result()
    return session_prefix.upper() + '-' + output_format


def ccg_parse(client, sentence, session_id=DEFAULT_SESSION, timeout=0):
    """Parse the sentence using the specified session.

    Args:
        client: The client end-point stub returned from get_client_transport()
        sentence: The sentence. Can be unicode, utf-8, or ascii.
        session_id: Optional session id.
        timeout: If non-zero make the call asynchronously with timeout equal to this value.
            Typically not needed unless the call may timeout when run synchronously.

    Returns:
        The response message string .
    """
    isUnicode = isinstance(sentence, unicode)
    if isUnicode:
        # CCG Parser is Java so input must be utf-8 or ascii
        sentence = sentence.encode('utf-8')
    query_input = create_query_input('text', sentence)
    request = Request()
    request.LUCID = session_id
    request.spec.name = 'infer'
    request.spec.content.extend([query_input])
    if timeout <= 0:
        response = client.infer(request)
    else:
        infer_future = client.infer.future(request, timeout)
        # FIXME: Need to add error reporting to Response structure.
        response = infer_future.result()
    if future_string == unicode:
        isUnicode = True
    if isinstance(response.msg, unicode):
        return response.msg if isUnicode else safe_utf8_encode(response.msg)
    return response.msg if not isUnicode else safe_utf8_decode(response.msg)


class CcgParserService:
    """Ccg Parser Service"""
    _WAIT_TIME = 30

    def __init__(self, daemon, workdir=None, jarfile=None, extra_args=None, debug=False):
        """Create a CCG Parse Service.

        Args:
            daemon: 'easysrl' or 'neuralccg'.
            workdir: Optional path to daemon if in release mode.
        """
        global _logger, _GRPC_RUNNING
        self.workdir = safe_utf8_encode(workdir) if workdir else os.getcwd()
        self.grpc_stop_onclose = False
        self.daemon_name = safe_utf8_encode(daemon)
        self.child = None
        extra_args = None if extra_args is None else [safe_utf8_encode(a) for a in extra_args]
        try:
            # Check if easyxxx service has started. If not start it.
            self.grpc_stub, _ = get_client_transport('localhost', self.daemon_port)
            ccg_parse(self.grpc_stub, '')
        except Exception:
            # Not started
            _logger.info('Starting %s gRPC daemon', self.daemon_name)

            if USE_DEVEL_PATH and jarfile is None:
                cmdline = [os.path.join(PROJDIR, 'scripts', 'start_server.sh'), daemon]
                if extra_args is not None:
                    cmdline.extend(extra_args)
                subprocess.call(cmdline)
                time.sleep(self._WAIT_TIME)   # Give it some time to lock session access
            elif jarfile is not None:
                log_file = os.path.join(workdir, self.daemon_name + '.log')
                cmdline = ['/usr/bin/java', '-Dlog4j.debug', '-jar', jarfile, '--daemonize']
                if extra_args is not None:
                    cmdline.extend(extra_args)
                _logger.debug(cmdline)
                if debug:
                    self.child = subprocess.Popen(cmdline)
                else:
                    self.child = subprocess.Popen(cmdline, stderr=open('/dev/null', 'w'))
                time.sleep(self._WAIT_TIME)
                os.kill(self.child.pid, 0)
                self.grpc_stop_onclose = True
                _logger.info('started child daemon with pid %d', self.child.pid)
            else:
                raise ValueError('CcgParserService.__init__()')
            _GRPC_RUNNING.add(self)
            self.stub, _ = get_client_transport('localhost', self.daemon_port)
            # Call asynchronously - will wait until default session is created
            ccg_parse(self.stub, '', timeout=120)
            self.grpc_stop_onclose = True

    @property
    def daemon_port(self):
        """Get the port of the gRPC service"""
        global EASYSRL_PORT, NEURALCCG_PORT
        return EASYSRL_PORT if self.daemon_name == 'easysrl' else NEURALCCG_PORT

    def open_client(self):
        """Open a connection to the gRPC service"""
        if self.grpc_stub:
            stub = self.grpc_stub
            self.grpc_stub = None
            return stub
        return get_client_transport('localhost', self.daemon_port)

    def shutdown(self):
        """Shutdown the gRPC service if it was opened by this application."""
        global _logger, _GRPC_RUNNING
        if self.grpc_stop_onclose:
            self.grpc_stop_onclose = False
            _GRPC_RUNNING.remove(self)
            _logger.info('Stopping %s gRPC daemon', self.daemon_name)
            if self.child is None:
                subprocess.call([os.path.join(PROJDIR, 'scripts', 'stop_server.sh'),
                                 self.daemon_name])
            else:
                self.child.terminate()
                for i in range(10):
                    time.sleep(0.5)
                    self.child.poll()
                    if self.child.returncode is not None:
                        break


def get_infox_client_transport(host, port=INFOX_PORT, timeout=60):
    """Open a connection to the gRPC service endpoint

    Args:
        host: The host domain name. Set to local_host if running locally.
        port: The service port.
        timeout: The maximum time to wait for the service to start.

    Returns:
        A tuple of the client end-point stub and channel
    """
    channel = grpc.insecure_channel('%s:%u' % (host, port))
    stub = InfoxServiceStub(channel)

    if timeout <= 0:
        stub.ping(empty_pb2.Empty())
    else:
        ping_future = stub.ping.future(empty_pb2.Empty(), timeout)
        ping_future.result()
    return stub, channel


