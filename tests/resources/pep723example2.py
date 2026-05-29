# /// script
# dependencies = ["requests"]
#
# [tool.uv.sources]
# requests = { git = "https://github.com/psf/requests" }
# ///

import requests

print(requests.__version__)
