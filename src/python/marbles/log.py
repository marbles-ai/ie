from __future__ import unicode_literals, print_function
import logging
import inspect
import time
import sys
from marbles import Properties, isdebugging


class ExceptionRateLimitedLogAdaptor(logging.LoggerAdapter, object):
    '''Rate limit exception log adaptor.'''

    def __init__(self, logger, rlimit=None):
        """Constructor.

        Args:
            logger: A logger instance.
            rlimit: The rate limit value. Zero disables. If None then the default of marbles.Properties.exception_rlimit
                is used.
        """
        super(self.__class__, self).__init__(logger, {})
        self.error_cache = {}
        self.logger = logger
        self.rlimit = rlimit or Properties.exception_rlimit
        self.last_update_time = time.time()

    def find_caller(self):
        if sys.exc_info()[2]:
            return sys.exc_info()[2].tb_frame.f_code.co_filename, sys.exc_info()[2].tb_lineno
        frmrec = inspect.stack()[2]
        return frmrec[1:4]

    def exception(self, msg, *args, **kwargs):
        """Logs an exception with rate limiting when form the same exception source. Arguments are the same as for
        logger function of the same name except one extra keyword argument allows extra information to be used to determine the exception source.

        Logging form teh same exeception source is ratelimited

        Args:
            msg: The error message
            rlimitby: Extra keyword argument to uniquely define the exception source. The default is file name, line
                number, and exception type.
        """
        if self.rlimit > 0:
            extra_args = map(lambda y: y[1], filter(lambda x: x[0] == 'rlimitby', kwargs.iteritems()))
            exc_info = filter(lambda x: x[0] == 'exc_info' and isinstance(x[1], Exception), kwargs.iteritems())
            kwargs = dict(filter(lambda x: x[0] != 'rlimitby' and isinstance(x[1], Exception), kwargs.iteritems()))
            extra = ''.join(extra_args)
            caller = self.find_caller()
            if len(exc_info) == 0:
                callerid = "%s:%s:%s" % (caller[0], caller[1], extra)
            else:
                callerid = "%s:%s:%d:%s" % (type(exc_info[0][1]).__name__, caller[0], caller[1], extra)
            del caller  # prevent GC issues - see traceback source

            tmnew = time.time()

            # Regularly clear cache to recover memory
            if (tmnew - self.last_update_time) > (2*self.rlimit):
                self.error_cache = {}
            self.last_update_time = tmnew

            if callerid in self.error_cache:
                tmold = self.error_cache[callerid]
                self.error_cache[callerid] = tmnew
                tmdiff = tmnew - tmold
                # If tmdiff < 0 then the system clock has changed
                if tmdiff < self.rlimit and tmdiff >= 0:
                    return
            else:
                self.error_cache[callerid] = tmnew
        super(ExceptionRateLimitedLogAdaptor, self).exception(msg, *args, **kwargs)


def set_log_format(log_handler):
    """Make some attempt to comply with RFC5424 and java."""
    #log_handler.setFormatter(logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s'))
    formatter = logging.Formatter(fmt='%(levelname)s %(asctime)s %(name)s %(process)d - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S%z')
    log_handler.setFormatter(formatter)


def setup_debug_logging():
    """Setup logging for scripts and debugging"""
    # Setup logging
    root_logger = logging.getLogger('marbles')
    log_level = logging.DEBUG if isdebugging() else logging.INFO
    root_logger.setLevel(log_level)
    console_handler = logging.StreamHandler()
    set_log_format(console_handler)
    root_logger.addHandler(console_handler)
