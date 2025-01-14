import sys
from typing import Any, Optional, Iterable

from httpie.cookies import HTTPieCookiePolicy
from http import cookiejar  # noqa

import niquests
from niquests._compat import HAS_LEGACY_URLLIB3


# to understand why this is required
# see https://niquests.readthedocs.io/en/latest/community/faq.html#what-is-urllib3-future
# short story, urllib3 (import/top-level import) may be the legacy one https://github.com/urllib3/urllib3
# instead of urllib3-future https://github.com/jawah/urllib3.future used by Niquests
# or only the secondary entry point could be available (e.g. urllib3_future on some distro without urllib3)
if not HAS_LEGACY_URLLIB3:
    # noinspection PyPackageRequirements
    import urllib3  # noqa: F401
    from urllib3.util import SKIP_HEADER, SKIPPABLE_HEADERS, parse_url, Timeout  # noqa: F401
    from urllib3.fields import RequestField, format_header_param_rfc2231  # noqa: F401
    from urllib3.util.ssl_ import (  # noqa: F401
        create_urllib3_context,
        resolve_ssl_version,
    )
else:
    # noinspection PyPackageRequirements
    import urllib3_future as urllib3  # noqa: F401
    from urllib3_future.util import SKIP_HEADER, SKIPPABLE_HEADERS, parse_url, Timeout  # noqa: F401
    from urllib3_future.fields import RequestField, format_header_param_rfc2231  # noqa: F401
    from urllib3_future.util.ssl_ import (  # noqa: F401
        create_urllib3_context,
        resolve_ssl_version,
    )

# Importlib_metadata was a provisional module, so the APIs changed quite a few times
# between 3.8-3.10. It was also not included in the standard library until 3.8, so
# we install the backport for <3.8.
if sys.version_info >= (3, 8):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

is_windows = 'win32' in str(sys.platform).lower()
is_frozen = getattr(sys, 'frozen', False)

MIN_SUPPORTED_PY_VERSION = (3, 7)
MAX_SUPPORTED_PY_VERSION = (3, 11)

# Request does not carry the original policy attached to the
# cookie jar, so until it is resolved we change the global cookie
# policy. <https://github.com/psf/requests/issues/5449>
cookiejar.DefaultCookiePolicy = HTTPieCookiePolicy


def has_ipv6_support(new_value: Optional[bool] = None) -> bool:
    if new_value is not None:
        # Allow overriding the default value for testing purposes.
        urllib3.util.connection.HAS_IPV6 = new_value
    return urllib3.util.connection.HAS_IPV6


def enforce_niquests():
    """
    Force imported 3rd-party plugins to use `niquests` instead of `requests` if they haven’t migrated yet.

    It’s a drop-in replacement for Requests so such plugins might continue to work unless they touch internals.

    """
    sys.modules["requests"] = niquests
    sys.modules["requests.adapters"] = niquests.adapters
    sys.modules["requests.sessions"] = niquests.sessions
    sys.modules["requests.exceptions"] = niquests.exceptions
    sys.modules["requests.packages.urllib3"] = urllib3


try:
    from functools import cached_property
except ImportError:
    # Can be removed once we drop Python <3.8 support.
    # Taken from `django.utils.functional.cached_property`.
    class cached_property:
        """
        Decorator that converts a method with a single self argument into a
        property cached on the instance.

        A cached property can be made out of an existing method:
        (e.g. ``url = cached_property(get_absolute_url)``).
        The optional ``name`` argument is obsolete as of Python 3.6 and will be
        deprecated in Django 4.0 (#30127).
        """
        name = None

        @staticmethod
        def func(instance):
            raise TypeError(
                'Cannot use cached_property instance without calling '
                '__set_name__() on it.'
            )

        def __init__(self, func, name=None):
            self.real_func = func
            self.__doc__ = getattr(func, '__doc__')

        def __set_name__(self, owner, name):
            if self.name is None:
                self.name = name
                self.func = self.real_func
            elif name != self.name:
                raise TypeError(
                    "Cannot assign the same cached_property to two different names "
                    "(%r and %r)." % (self.name, name)
                )

        def __get__(self, instance, cls=None):
            """
            Call the function and put the return value in instance.__dict__ so that
            subsequent attribute access on the instance returns the cached value
            instead of calling cached_property.__get__().
            """
            if instance is None:
                return self
            res = instance.__dict__[self.name] = self.func(instance)
            return res


def find_entry_points(entry_points: Any, group: str) -> Iterable[importlib_metadata.EntryPoint]:
    if hasattr(entry_points, "select"):  # Python 3.10+ / importlib_metadata >= 3.9.0
        return entry_points.select(group=group)
    else:
        return set(entry_points.get(group, ()))


def get_dist_name(entry_point: importlib_metadata.EntryPoint) -> Optional[str]:
    dist = getattr(entry_point, "dist", None)
    if dist is not None:  # Python 3.10+
        return dist.name

    match = entry_point.pattern.match(entry_point.value)
    if not (match and match.group('module')):
        return None

    package = match.group('module').split('.')[0]
    try:
        metadata = importlib_metadata.metadata(package)
    except importlib_metadata.PackageNotFoundError:
        return None
    else:
        return metadata.get('name')
