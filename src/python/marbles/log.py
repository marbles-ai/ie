from __future__ import unicode_literals, print_function
import logging
import inspect
import time
from marbles import Properties


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
        frmrec = inspect.stack()[2]
        return frmrec[1:4]

    def exception(self, msg, *args, **kwargs):
        """Logs an exception with rate limiting."""
        if self.rlimit > 0:
            exc_info = filter(lambda x: x[0] == 'exc_info' and isinstance(x[1], Exception), kwargs.iteritems())
            caller = self.find_caller()
            if len(exc_info) == 0:
                callerid = "%s:%s" % (caller[0], caller[1])
            else:
                callerid = "%s:%s:%d" % (type(exc_info[0][1]).__name__, caller[0], caller[1])

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

