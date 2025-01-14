"""Tests for dealing with binary request and response data."""
import niquests

from .fixtures import BIN_FILE_PATH, BIN_FILE_CONTENT, BIN_FILE_PATH_ARG
from httpie.output.streams import BINARY_SUPPRESSED_NOTICE
from .utils import MockEnvironment, http


class TestBinaryRequestData:

    def test_binary_stdin(self, httpbin):
        with open(BIN_FILE_PATH, 'rb') as stdin:
            env = MockEnvironment(
                stdin=stdin,
                stdin_isatty=False,
                stdout_isatty=False
            )
            r = http('--print=B', 'POST', httpbin + '/post', env=env)
            assert r == BIN_FILE_CONTENT

    def test_binary_file_path(self, httpbin):
        env = MockEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=B', 'POST', httpbin + '/post',
                 '@' + BIN_FILE_PATH_ARG, env=env)
        assert r == BIN_FILE_CONTENT

    def test_binary_file_form(self, httpbin):
        env = MockEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--print=B', '--form', 'POST', httpbin + '/post',
                 'test@' + BIN_FILE_PATH_ARG, env=env)
        assert bytes(BIN_FILE_CONTENT) in bytes(r)


class TestBinaryResponseData:
    # Local httpbin crashes due to an unfixed bug — it is merged but not yet released.
    # <https://github.com/psf/httpbin/pull/41>
    # TODO: switch to the local `httpbin` fixture when the fix is released.

    def test_binary_suppresses_when_terminal(self, remote_httpbin):
        r = http('GET', remote_httpbin + '/bytes/1024?seed=1')
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_binary_suppresses_when_not_terminal_but_pretty(self, remote_httpbin):
        env = MockEnvironment(stdin_isatty=True, stdout_isatty=False)
        r = http('--pretty=all', 'GET', remote_httpbin + '/bytes/1024?seed=1', env=env)
        assert BINARY_SUPPRESSED_NOTICE.decode() in r

    def test_binary_included_and_correct_when_suitable(self, remote_httpbin):
        env = MockEnvironment(stdin_isatty=True, stdout_isatty=False)
        url = remote_httpbin + '/bytes/1024?seed=1'
        r = http('GET', url, env=env)
        expected = niquests.get(url).content
        assert r == expected
