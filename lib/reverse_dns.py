import json


def load_rdns_table(rdns_fp):
    rdns_file = open(rdns_fp, "r")
    return json.loads(rdns_file.read())


def query(ip, rdns):
    try:
        return rdns[ip]
    except KeyError:
        return ip