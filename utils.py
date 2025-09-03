"""Miscellaneous stuff."""

import functools


def call_once(func):
    """Decorator that makes decorated function to be called
    at most once.
    """
    is_called = False
    @functools.wraps(func)
    def wrapper():
        nonlocal is_called
        if not is_called:
            func()
            is_called = True
    return wrapper
