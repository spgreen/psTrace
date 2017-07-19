import json
import ssl
import urllib.request


def update_dictionary_from_json_file(dictionary_contents, fp):
    """
    Updates dictionary with JSON file contents defined by the fp parameter???????
    :param dictionary_contents: dictionary to be updated
    :param fp: file path of the JSON file to load
    :return: 
    """
    try:
        with open(fp, "r") as file:
            dictionary_contents.update(json.load(fp=file))
    except FileNotFoundError:
        print("File %s not found!" % fp)
    except ValueError:
        print("Error: Unable to update due to different dictionary_contents length")
    return


def save_dictionary_as_json_file(dictionary_contents, fp):
    """
    
    :param dictionary_contents: dictionary to be saved as a JSON file
    :param fp: file path of JSON to be saved
    :return: 
    """
    try:
        with open(fp, "w") as file:
            json.dump(obj=dictionary_contents, fp=file, indent=4)
    except FileNotFoundError:
        print("Directory %s does not exist" % fp)
    return


def retrieve_json_from_url(json_url, url_encoding='utf-8'):
    """
    
    :param json_url: 
    :param url_encoding: 
    :return: 
    """
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
    try:
        json_data = urllib.request.urlopen(json_url, timeout=10, context=ssl_context)
    except urllib.error.URLError:
        print("Retrieval failed")
        return
    json_string = json_data.read().decode(url_encoding)
    return json.loads(json_string)