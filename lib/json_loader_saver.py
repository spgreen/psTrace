import json
import ssl
import urllib.request


def save_dictionary_as_json_file(dictionary_contents, file_path):
    """
    
    :param dictionary_contents: dictionary to be saved as a JSON file
    :param file_path: file path of JSON to be saved
    :return: 
    """
    try:
        with open(file_path, "w") as file:
            json.dump(obj=dictionary_contents, fp=file, indent=4)
    except FileNotFoundError:
        print("Directory %s does not exist" % file_path)
    return


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
