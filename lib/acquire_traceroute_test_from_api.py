import json
import ssl
import urllib.request
import urllib.parse


def retrieve_json_from_url(json_url, url_encoding='utf-8'):
    """
    
    :param json_url: 
    :param url_encoding: 
    :return: 
    """
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
    try:
        ps_json_url = urllib.request.urlopen(json_url, timeout=10, context=ssl_context)
    except urllib.error.URLError:
        print("Retrieval failed")
        return
    ps_json_str = ps_json_url.read().decode(url_encoding)
    return json.loads(ps_json_str)


def acquire_traceroute_tests(ps_node_url, test_time_range=2400):
    """
    
    :param ps_node_url: 
    :param test_time_range: 
    :return: 
    """
    base_measurement_url = "/esmond/perfsonar/archive/?event-type=packet-trace&time-range="
    test_time_range = str(test_time_range)

    traceroute_tests = retrieve_json_from_url("https://" + ps_node_url + base_measurement_url + "1200")
    data_dict = dict()
    for singular_test in traceroute_tests:
        input_destination = singular_test['input-destination']
        if input_destination not in data_dict:
            data_dict[input_destination] = {}
            url = urllib.parse.urlsplit(singular_test['url'], scheme="https")
            data_dict[input_destination]['api'] = "https://" + url.netloc + url.path + "packet-trace/base?time-range=" + test_time_range  # replaces http scheme with https
            data_dict[input_destination]['source'] = singular_test['source']
            data_dict[input_destination]['destination'] = singular_test['destination']

    return data_dict
