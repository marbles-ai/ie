#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import os
import signal
import time
import sys
import daemon.pidfile
import watchtower
import pwd
import grp
from marbles.log import ExceptionRateLimitedLogAdaptor, set_log_format


_module_logger = logging.getLogger(__name__)


class ServiceState(object):
    def __init__(self, logger=None):
        self.pass_on_exceptions = False
        if logger is not None and not isinstance(logger, ExceptionRateLimitedLogAdaptor):
            self.logger = ExceptionRateLimitedLogAdaptor(logger)
        else:
            self.logger = logger

    @property
    def terminate(self):
        return False

    def wait(self, seconds):
        time.sleep(seconds)

    def time(self):
        return time.time()


# Signal handlers
hup_recv = 0
def hup_handler(signum, frame):
    global hup_recv
    hup_recv += 1
    _module_logger.info('SIGHUP')

terminate = False
def term_handler(signum, frame):
    global terminate, logger
    terminate = True
    _module_logger.info('SIGTERM')


def alarm_handler(signum, frame):
    pass


class DefaultServiceState(ServiceState):
    """Default service state"""

    def __init__(self, svcname=None, logger=None, root_logger=None, rundir=None, pidfile=None,
                 daemonize=False, uid=None, gid=None):
        super(DefaultServiceState, self).__init__(logger=logger)
        self.svcname = svcname if svcname is not None else 'unknown'
        self.root_logger = root_logger
        self.rundir = rundir
        self.pidfile = pidfile
        self.daemonize = daemonize
        self.uid = uid
        self.gid = gid

    @property
    def terminate(self):
        global terminate
        return terminate

    def wait(self, seconds):
        self.logger.debug('Pausing for %s seconds', seconds)
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(seconds)
        if not self.terminate:
            # FIXME: We have a race condition here.
            # If SIGTERM arrives just before the pause call we miss it for `seconds`.
            # A second SIGTERM will help
            signal.pause()
        self.logger.debug('Continue')


class ServiceExecutor(object):

    def __init__(self, wakeup, state_or_logger=None):
        """Constructor

        Args:
            wakeup: Max timetosleep before calling on_wakeup().
            state_or_logger
        """
        self.wakeup = wakeup
        if state_or_logger is None:
            self.state = DefaultServiceState()
        elif isinstance(state_or_logger, ServiceState):
            self.state = state_or_logger
        elif isinstance(state_or_logger, (logging.LoggerAdapter, logging.Logger)):
            self.state = DefaultServiceState(logger=state_or_logger)
        else:
            raise TypeError('state_or_logger must be a ServiceState, Logger, or LoggerAdaptor')

    def _run_loop(self):
        global hup_recv
        count = 0

        while not self.state.terminate:
            # A HUP increments hup_recv.
            hup_recv_local = hup_recv
            hup_signaled = hup_recv_local != count  # test
            count = hup_recv_local                  # set

            if hup_signaled:
                self.logger.info('HUP received, refreshing')
                self.on_hup()
            else:
                self.on_wake()
                # If force_terminate() was called then exit
                if self.state.terminate:
                    break
                self.state.wait(self.wakeup)

        self.logger.info('TERM received, exited daemon run loop')
        self.on_term(True)

    @property
    def logger(self):
        return self.state.logger

    def force_terminate(self):
        """Force termination of the run loop"""
        global terminate
        terminate = True

    def force_hup(self):
        """Force on_hup() to be called."""
        global hup_recv
        hup_recv += 1

    def on_hup(self):
        """Called when SIGHUP is received."""
        pass

    def on_term(self, graceful):
        """Called when SIGTERM is received."""
        pass

    def on_wake(self):
        """Called regularly in run loop."""
        pass

    def on_start(self, workdir):
        """Called just before entering the run-loop. Dependent services should be started here.

        Args:
            workdir: The working directory.
        """
        pass

    def on_shutdown(self):
        """Called after on_term, just before logging shutdown. Dependent services should be stopped here."""
        pass

    def run(self, workdir):
        """Run the daemon.

        Args:
            workdir: The working directory.

        Remarks:
            Do not overide this function.
        """
        if workdir is None:
            workdir = os.getcwdu()

        if self.state.daemonize:
            if not os.path.exists(self.state.rundir):
                os.makedirs(self.state.rundir, 0o777)
            if not os.path.isdir(self.state.rundir):
                print('%s is not a directory' % self.state.rundir)
                sys.exit(1)
            print('Starting service')

            context = daemon.DaemonContext(working_directory=workdir,
                                           umask=0o022,
                                           pidfile=daemon.pidfile.PIDLockFile(self.state.pidfile),
                                           gid=self.state.gid,
                                           uid=self.state.uid,
                                           signal_map = {
                                               signal.SIGTERM: term_handler,
                                               signal.SIGHUP:  hup_handler,
                                               signal.SIGALRM: alarm_handler,
                                           })
            started = False
            try:
                with context:
                    self.on_start(workdir)
                    started = True
                    self.logger.info('Service started')
                    self._run_loop()

            except Exception as e:
                self.logger.exception('Exception caught', exc_info=e)
                if not started:
                    print('An error occured starting service')
                else:
                    try:
                        self.on_term(False)
                    except Exception as et:
                        self.logger.exception('Exception caught during on_term()', exc_info=et)

        else:
            started = False
            graceful = True
            try:
                signal.signal(signal.SIGTERM, term_handler)
                signal.signal(signal.SIGHUP, hup_handler)
                signal.signal(signal.SIGALRM, alarm_handler)
                self.on_start(workdir)
                started = True
                self.logger.info('Service started')
                self._run_loop()

            except KeyboardInterrupt:
                self.logger.debug('KeyboardInterrupt')
                pass

            except Exception as e:
                self.logger.exception('Exception caught', exc_info=e)
                graceful = False

            if started:
                try:
                    self.on_term(graceful)
                except Exception as et:
                    self.logger.exception('Exception caught during on_term()', exc_info=et)

        try:
            self.on_shutdown()
        except Exception as e:
            logger.exception('Exception caught', exc_info=e)

        self.logger.info('Service stopped')
        logging.shutdown()
        if self.state.daemonize:
            try:
                os.remove(self.state.pidfile)
            except:
                pass


def init_log_handler(log_handler, log_level):
    log_handler.setLevel(log_level)
    set_log_format(log_handler)


def init_parser_options(parser):
    """Initialize the option parser.

    Args:
        parser: An OptionParser instance.
    """
    parser.add_option('-l', '--log-level', type='string', action='store', dest='log_level',
                      help='Logging level, defaults to \"info\"')
    parser.add_option('-f', '--log-file', type='string', action='store', dest='log_file',
                      help='Logging file, defaults to console or AWS CloudWatch when running as a daemon.')
    parser.add_option('-F', '--ghost-log-file', type='string', action='store', dest='ghost_log_file',
                      help='Logging file for ghostdriver, defaults to /working/dir/ghostdriver.log')
    parser.add_option('-d', '--daemonize', action='store_true', dest='daemonize', default=False,
                      help='Run as a daemon.')
    parser.add_option('-U', '--user', type='string', action='store', dest='user',
                      help='Runs the daemon in the user context. A name or uid can be given.')
    parser.add_option('-G', '--group', type='string', action='store', dest='group',
                      help='Runs the daemon in the group context. A name or gid can be given.')
    parser.add_option('-p', '--pid-file', type='string', action='store', dest='pid_file',
                      help='PID lock file, defaults to the current directory.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Verbose output.')


def process_parser_options(options, svc_name, stream_name=None):
    """Process standard parser service options.

    Args:
        options: An Options instance.
        svc_name: The service name.

    Returns:
        A DefaultServiceState instance.
    """
    try:
        uid = None if options.user is None else int(options.user)
    except:
        uid = None if options.user is None else pwd.getpwnam(options.user)[2]
    try:
        gid = None if options.group is None else int(options.group)
    except:
        gid = None if options.group is None else grp.getgrnam(options.group)[2]

    if gid is not None:
        # Check group if exists
        grp.getgrgid(gid)
    if uid is not None:
        # Check user if exists
        pwd.getpwuid(uid)

    # Setup logging
    log_level = getattr(logging, options.log_level.upper()) if options.log_level else logging.INFO
    root_logger = logging.getLogger('marbles')
    root_logger.setLevel(log_level)
    actual_logger = logging.getLogger('marbles.svc.' + svc_name)
    logger = ExceptionRateLimitedLogAdaptor(actual_logger)
    if stream_name is None:
        stream_name = 'svc-' + svc_name

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
                                                      stream_name=stream_name,
                                                      create_log_group=False)
    init_log_handler(log_handler, log_level)
    root_logger.addHandler(log_handler)

    if options.pid_file is None:
        rundir = os.path.join(os.getcwdu(), 'run')
        pid_file = os.path.join(rundir, svc_name + '.pid')
    else:
        pid_file = os.path.abspath(options.pid_file)
        rundir = os.path.dirname(pid_file)

    return DefaultServiceState(svcname=svc_name, logger=logger, root_logger=root_logger,
                               rundir=rundir, pidfile=pid_file, daemonize=options.daemonize,
                               uid=uid, gid=gid)

