import os
import unittest
from contextlib import contextmanager
from distutils.util import strtobool
from enum import Enum
from unittest.mock import patch


SMALL_MODEL_IDENTIFIER = "julien-c/bert-xsmall-dummy"
DUMMY_UNKWOWN_IDENTIFIER = "julien-c/dummy-unknown"
DUMMY_DIFF_TOKENIZER_IDENTIFIER = "julien-c/dummy-diff-tokenizer"
# Example model ids

SAMPLE_DATASET_IDENTIFIER = "lhoestq/custom_squad"
# Example dataset ids


def parse_flag_from_env(key, default=False):
    try:
        value = os.environ[key]
    except KeyError:
        # KEY isn't set, default to `default`.
        _value = default
    else:
        # KEY is set, convert it to True or False.
        try:
            _value = strtobool(value)
        except ValueError:
            # More values are supported, but let's keep the message simple.
            raise ValueError("If set, {} must be yes or no.".format(key))
    return _value


def parse_int_from_env(key, default=None):
    try:
        value = os.environ[key]
    except KeyError:
        _value = default
    else:
        try:
            _value = int(value)
        except ValueError:
            raise ValueError("If set, {} must be a int.".format(key))
    return _value


_run_git_lfs_tests = parse_flag_from_env("RUN_GIT_LFS_TESTS", default=False)


def require_git_lfs(test_case):
    """
    Decorator marking a test that requires git-lfs.

    git-lfs requires additional dependencies, and tests are skipped by default. Set the RUN_GIT_LFS_TESTS environment
    variable to a truthy value to run them.
    """
    if not _run_git_lfs_tests:
        return unittest.skip("test of git lfs workflow")(test_case)
    else:
        return test_case


class RequestWouldHangIndefinitelyError(Exception):
    pass


class OfflineSimulationMode(Enum):
    CONNECTION_FAILS = 0
    CONNECTION_TIMES_OUT = 1
    HF_HUB_OFFLINE_SET_TO_1 = 2


@contextmanager
def offline(mode=OfflineSimulationMode.CONNECTION_FAILS, timeout=1e-16):
    """
    Simulate offline mode.

    There are three offline simulatiom modes:

    CONNECTION_FAILS (default mode): a ConnectionError is raised for each network call.
        Connection errors are created by mocking socket.socket
    CONNECTION_TIMES_OUT: the connection hangs until it times out.
        The default timeout value is low (1e-16) to speed up the tests.
        Timeout errors are created by mocking requests.request
    HF_HUB_OFFLINE_SET_TO_1: the HF_HUB_OFFLINE_SET_TO_1 environment variable is set to 1.
        This makes the http/ftp calls of the library instantly fail and raise an OfflineModeEmabled error.
    """
    import socket

    from requests import request as online_request

    def timeout_request(method, url, **kwargs):
        # Change the url to an invalid url so that the connection hangs
        invalid_url = "https://10.255.255.1"
        if kwargs.get("timeout") is None:
            raise RequestWouldHangIndefinitelyError(
                f"Tried a call to {url} in offline mode with no timeout set. Please set a timeout."
            )
        kwargs["timeout"] = timeout
        try:
            return online_request(method, invalid_url, **kwargs)
        except Exception as e:
            # The following changes in the error are just here to make the offline timeout error prettier
            e.request.url = url
            max_retry_error = e.args[0]
            max_retry_error.args = (
                max_retry_error.args[0].replace("10.255.255.1", f"OfflineMock[{url}]"),
            )
            e.args = (max_retry_error,)
            raise

    def offline_socket(*args, **kwargs):
        raise socket.error("Offline mode is enabled.")

    if mode is OfflineSimulationMode.CONNECTION_FAILS:
        # inspired from https://stackoverflow.com/a/18601897
        with patch("socket.socket", offline_socket):
            yield
    elif mode is OfflineSimulationMode.CONNECTION_TIMES_OUT:
        # inspired from https://stackoverflow.com/a/904609
        with patch("requests.request", timeout_request):
            yield
    elif mode is OfflineSimulationMode.HF_HUB_OFFLINE_SET_TO_1:
        with patch("huggingface_hub.constants.HF_HUB_OFFLINE", True):
            yield
    else:
        raise ValueError("Please use a value from the OfflineSimulationMode enum.")
