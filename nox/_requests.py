try:
    import requests

    def requests_get_status_code(url):
        return requests.get(url).status_code

except ImportError:
    import sys
    from urllib.parse import urlparse

    if sys.version_info < (3, ):
        from urllib import getproxies
    else:
        from urllib.request import getproxies

    from http.client import HTTPConnection, HTTPSConnection

    try:
        import importlib.metadata as metadata
    except ImportError:  # pragma: no cover
        import importlib_metadata as metadata

    nox_version = metadata.version("nox")

    def requests_get_status_code(url):
        # Split the url into scheme hostname and path
        u = urlparse(url)

        # Make sure that the environment has no specific proxy configuration as we are not able to manage
        env_proxies = getproxies()
        if u.scheme.lower() in env_proxies:
            raise ValueError("HTTP(s) proxies are not supported by `nox` out of the box. Please `pip install requests`")

        # Perform a GET and return the status code
        headers = {'User-Agent': 'python-nox/%s' % nox_version,
                   # 'Accept-Encoding': 'gzip, deflate',
                   'Accept': '*/*',
                   'Connection': 'keep-alive'}
        try:
            if u.scheme == 'http':
                h1 = HTTPConnection(host=u.hostname, port=u.port)
            else:
                h1 = HTTPSConnection(host=u.hostname, port=u.port)
            h1.request("GET", u.path, body=None, headers=headers, encode_chunked=False)
            code = h1.getresponse().status
        finally:
            h1.close()

        return code
