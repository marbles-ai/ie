import os

PROJDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
USE_DEVEL_PATH = os.path.exists(os.path.join(PROJDIR, 'src', 'python', 'marbles'))


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
