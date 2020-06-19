try:
    import requests

    def requests_get_status_code(url):
        return requests.get(url).status_code

except ImportError:
    import sys

    if sys.version_info < (3, ):
        from urllib import getproxies
    else:
        from urllib.request import getproxies

    from urllib3.poolmanager import PoolManager
    from urllib3.util import parse_url, Timeout as TimeoutSauce
    from urllib3.util.retry import Retry
    from urllib3.exceptions import LocationValueError

    try:
        import importlib.metadata as metadata
    except ImportError:  # pragma: no cover
        import importlib_metadata as metadata

    nox_version = metadata.version("nox")

    def requests_get_status_code(url):
        # Make sure that the environment has no specific proxy configuration as we are not able to manage
        env_proxies = getproxies()
        if 'http' in env_proxies:
            raise ValueError("HTTP(s) proxies are not supported by `nox` out of the box - please `pip install requests`")

        # Perform a GET and return the status code
        adapter = HTTPAdapter()
        try:
            code = adapter.send_get_and_return_status_code(url)
        finally:
            adapter.close()

        return code

    class InvalidURL(ValueError):
        """The URL is invalid"""

    class HTTPAdapter(object):
        """A mini HTTP Adapter for urllib3 inspired by `requests`."""

        __slots__ = ('max_retries', 'poolmanager')

        def __init__(self):
            self.max_retries = Retry(0, read=False)
            self.poolmanager = PoolManager(num_pools=2, maxsize=2,
                                           block=False, strict=True)

        def close(self):
            self.poolmanager.clear()

        def send_get_and_return_status_code(self, url):
            try:
                u = parse_url(url)
                conn = self.poolmanager.connection_from_host(u.host,
                                                             port=u.port,
                                                             scheme=u.scheme)
            except LocationValueError as e:
                raise InvalidURL(e, url)

            # no proxy, no cert validation
            url = '/'
            headers = {'User-Agent': 'python-nox/%s' % nox_version,
                       'Accept-Encoding': 'gzip, deflate',
                       'Accept': '*/*',
                       'Connection': 'keep-alive'}

            resp = conn.urlopen(
                method='GET',
                url=url,
                body=None,
                headers=headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=TimeoutSauce(connect=None, read=None)
            )

            # return status code only
            return getattr(resp, 'status', None)
