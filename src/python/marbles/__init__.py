import os

PROJDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ROOTDIR = os.path.dirname(os.path.abspath(__file__))
USE_DEVEL_PATH = os.path.exists(os.path.join(PROJDIR, 'src', 'python', 'marbles'))
UNICODE_STRINGS = False

def safe_utf8_encode(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    elif not isinstance(s, str):
        return str(s)
    return s


def safe_utf8_decode(s):
    if isinstance(s, str):
        return s.decode('utf-8')
    elif not isinstance(s, str):
        return unicode(s)
    return s


native_string = str
future_string = unicode


class Properties(object):
    """Global properties used by sub-modules"""
    # Exception rate limit. Exceptions of the same type, from same caller and line number are
    # are rate limited to 1 every `exception_rlimit` seconds.
    exception_rlimit = 2.0


try:
    from marbles.test import isdebugging
    from marbles.test import dprint
except:
    def isdebugging():
        return False
    def dprint(*args, **kwargs):
        pass

