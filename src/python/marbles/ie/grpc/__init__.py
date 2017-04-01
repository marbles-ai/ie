from marbles_service_pb2 import LucidaServiceStub, QueryInput, QuerySpec, Request, Response
from google.protobuf import empty_pb2
import grpc
import os

## EasySRL gRPC service port
EASYSRL_PORT = 8084

## EasyCCG gRPC service port
EASYCCG_PORT = 8085

## Default Session Id
DEFAULT_SESSION='default'


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
        port: The service port. Either EASYSRL_PORT or EASYCCG_PORT.

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
        raise ValueError('bad output format passed to create_session')

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
        sentence: The utf-8 sentence. Do not pass unicode.
        session_id: Optional session id.
        timeout: If non-zero make the call asynchronously with timeout equal to this value.
            Typically not needed unless the call may timeout when run synchronously.

    Returns:
        The response message string .
    """
    query_input = create_query_input('text', sentence)
    request = Request()
    request.LUCID = session_id
    request.spec.name = 'infer'
    request.spec.content.extend([query_input])
    if timeout <= 0:
        response = client.infer(request)
        return response.msg
    else:
        infer_future = client.infer.future(request, timeout)
        # FIXME: Need to add error reporting to Response structure.
        response = infer_future.result()
        return response.msg
