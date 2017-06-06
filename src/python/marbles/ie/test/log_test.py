from __future__ import unicode_literals, print_function
import unittest
from marbles import log
import logging
import time


class TestHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super(TestHandler, self).__init__(*args, **kwargs)
        self.buffer = []
    def emit(self, record):
        self.buffer.append(record.msg)


class LogTest(unittest.TestCase):

    def test1_std_logging(self):
        logger = logging.getLogger('test1')
        logger.setLevel(logging.DEBUG)
        handler = TestHandler()
        logger.addHandler(handler)
        logger.debug('debug')
        logger.info('info')
        logger.warning('warning')
        logger.warn('warn')
        logger.error('error')
        logger.exception('exception')
        expected = [
            'debug',
            'info',
            'warning',
            'warn',
            'error',
            'exception'
        ]
        self.assertListEqual(expected, handler.buffer)
        logger.removeHandler(handler)

    def test2_std_logging(self):
        actual_logger = logging.getLogger('test2')
        actual_logger.setLevel(logging.DEBUG)
        handler = TestHandler()
        actual_logger.addHandler(handler)
        logger = log.ExceptionRateLimitedLogAdaptor(actual_logger)
        logger.debug('debug')
        logger.info('info')
        logger.warning('warning')
        logger.error('error')
        logger.exception('exception')
        expected = [
            'debug',
            'info',
            'warning',
            'error',
            'exception'
        ]
        self.assertListEqual(expected, handler.buffer)

    def test3_rate_limited_logging(self):
        actual_logger = logging.getLogger('test3')
        actual_logger.setLevel(logging.DEBUG)
        handler = TestHandler()
        actual_logger.addHandler(handler)
        logger = log.ExceptionRateLimitedLogAdaptor(actual_logger, 2.0)
        logger.debug('debug')
        logger.info('info')
        logger.warning('warning')
        logger.error('error')
        for i in range(3):
            logger.exception('exception%d' % (1+i))
            if i == 1:
                time.sleep(3.0)
        expected = [
            'debug',
            'info',
            'warning',
            'error',
            'exception1',
            'exception3'
        ]
        self.assertListEqual(expected, handler.buffer)

    def test4_rate_limited_logging(self):
        actual_logger = logging.getLogger('test3')
        actual_logger.setLevel(logging.DEBUG)
        handler = TestHandler()
        actual_logger.addHandler(handler)
        logger = log.ExceptionRateLimitedLogAdaptor(actual_logger, 2.0)
        logger.debug('debug')
        logger.info('info')
        logger.warning('warning')
        logger.error('error')
        for i in range(3):
            e = Exception('x%d' % i)
            logger.exception('exception%d' % (1+i), exc_info=e)
            if i == 1:
                time.sleep(3.0)
        expected = [
            'debug',
            'info',
            'warning',
            'error',
            'exception1',
            'exception3'
        ]
        self.assertListEqual(expected, handler.buffer)
        handler.buffer = []
        logger.debug('debug')
        for i in range(3):
            try:
                raise Exception('x%d' % i)
            except Exception as e:
                logger.exception('exception%d' % (1+i), exc_info=e)
            if i == 1:
                time.sleep(3.0)
        expected = [
            'debug',
            'exception1',
            'exception3'
        ]
        self.assertListEqual(expected, handler.buffer)
        handler.buffer = []
        logger.debug('debug')
        for i in range(3):
            try:
                raise Exception('x%d' % i)
            except Exception as e:
                logger.exception('exception%d' % (1+i), exc_info=e, rlimitby='x%d' % i)
            if i == 1:
                time.sleep(3.0)
        expected = [
            'debug',
            'exception1',
            'exception2',
            'exception3'
        ]
        self.assertListEqual(expected, handler.buffer)


if __name__ == '__main__':
    unittest.main()
