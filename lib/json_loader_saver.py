#!/usr/bin/python3
"""
TODO: Add Description
"""

import json
import ssl
import urllib.request

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


def retrieve_json_from_url(json_url, url_encoding='utf-8'):
    """
    TODO: Add Description
    :param json_url: 
    :param url_encoding: 
    :return: 
    """
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
    json_data = urllib.request.urlopen(json_url, timeout=10, context=ssl_context)
    json_string = json_data.read().decode(url_encoding)
    return json.loads(json_string)
