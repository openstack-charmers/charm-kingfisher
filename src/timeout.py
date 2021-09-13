#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
"""
Context manager to run tasks with a timeout.
"""

import contextlib
import errno
import os
import signal

DEFAULT_ERROR_MESSAGE = os.strerror(errno.ETIME)


class Timeout(contextlib.ContextDecorator):
    """
    Usage:

    try:
        with timeout.Timeout(seconds=10):
            time.sleep(11)
    except TimeoutError:
        logging.error("Timed out after 10 seconds")
    """
    def __init__(self, minutes: int, *, timeout_message: str = DEFAULT_ERROR_MESSAGE):
        self.seconds = int(minutes * 60)
        self.timeout_message = timeout_message

    def _timeout_handler(self, _signum, _frame):
        raise TimeoutError(self.timeout_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.seconds)

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        signal.alarm(0)
