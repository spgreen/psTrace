import json
import ssl
import urllib.request


def retrieve_json_from_url(json_url, url_encoding='utf-8'):
    """

    :param json_url: 
    :param url_encoding: 
    :return: 
    """
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
    json_data = urllib.request.urlopen(json_url, timeout=10, context=ssl_context)
    json_string = json_data.read().decode(url_encoding)
    return json.loads(json_string)
