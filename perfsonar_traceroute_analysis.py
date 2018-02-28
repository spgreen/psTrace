#!/usr/bin/python3
import argparse
import datetime
import os.path
import configparser
import urllib.parse

from urllib.error import HTTPError

from ps_classes import ReverseDNS
from ps_classes import PsTrace
from lib import json_loader_saver

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(BASE_DIR, 'config.ini'))

TESTING_PERIOD = int(CONFIG['PERFSONAR']['MAX_TIME_BETWEEN_TESTS'])
THRESHOLD = float(CONFIG['ROUTE_COMPARISON']['THRESHOLD'])
EMAIL_ALERTS = int(CONFIG['EMAIL']['ALERTS'])
EMAIL_TO = CONFIG['EMAIL']['TO'].replace(' ', '').split(',')
EMAIL_FROM = CONFIG['EMAIL']['FROM']
EMAIL_SUBJECT = CONFIG['EMAIL']['SUBJECT']
SMTP_SERVER = CONFIG['EMAIL']['SMTP_SERVER']

# Directories
HTML_DIR = os.path.join(BASE_DIR, "html")
JSON_DIR = os.path.join(BASE_DIR, "json")
TEMPLATE_DIR = os.path.join(BASE_DIR, "html_templates")

# HTML Folder
FORCE_GRAPH_DATA_FP = os.path.join(HTML_DIR, "traceroute_force_graph.json")
DASHBOARD_WEB_PAGE_FP = os.path.join(HTML_DIR, "index.html")

# JSON Folder
REVERSE_DNS_FP = os.path.join(JSON_DIR, "rdns.json")
PREVIOUS_ROUTE_FP = os.path.join(JSON_DIR, "previous_routes.json")

# Jinja2 Templates
J2_EMAIL_TEMPLATE_FP = os.path.join(TEMPLATE_DIR, "email.html.j2")
J2_TRACEROUTE_WEB_PAGE_FP = os.path.join(TEMPLATE_DIR, "traceroute.html.j2")
J2_MATRIX_WEB_PAGE_FP = os.path.join(TEMPLATE_DIR, "matrix.html.j2")


def acquire_traceroute_tests(ps_node_url, rdns_query, test_time_range=2400):
    """
    Acquires all recent traceroute results from a PerfSONAR Measurement Archive
    :param ps_node_url: Base URL of PerfSONAR MA
    :param test_time_range: time range in seconds of tests to retrieve
    :param rdns_query: Reverse DNS function
    :return: 
    """
    if not isinstance(test_time_range, int):
        raise ValueError

    ps_url = "https://%s/esmond/perfsonar/archive/?event-type=packet-trace&time-range=%d" % (ps_node_url, TESTING_PERIOD)
    traceroute_tests = json_loader_saver.retrieve_json_from_url(ps_url)

    data_list = []
    for singular_test in traceroute_tests:
        url = urllib.parse.urlsplit(singular_test['url'], scheme="https")
        api_key = "https://{}{}packet-trace/base?time-range={}".format(url.netloc, url.path, test_time_range)
        data_list.append({'api': api_key,
                          'source': singular_test['source'],
                          'destination': singular_test["destination"],
                          'source_domain': rdns_query(singular_test['source']),
                          'destination_domain': rdns_query(singular_test["destination"])})

    return data_list


def main(perfsonar_ma_url, time_period):
    """
    PSTRACE
    :param perfsonar_ma_url:
    :param time_period:
    :return:
    """
    rdns = ReverseDNS()
    # Loads reverse DNS information from a JSON file found at REVERSE_DNS_FP
    rdns.update_from_json_file(REVERSE_DNS_FP)
    rdns_query = rdns.query

    print("Acquiring traceroute tests... ", end="")

    try:
        traceroute_metadata = acquire_traceroute_tests(ps_node_url=perfsonar_ma_url,
                                                       rdns_query=rdns_query,
                                                       test_time_range=time_period)
        print("%d test(s) received!" % len(traceroute_metadata))
    except HTTPError as error:
        print("%s - Unable to retrieve perfSONAR traceroute data from %s" % (error, perfsonar_ma_url))
        exit()

    ps_trace = PsTrace(traceroute_metadata,
                       THRESHOLD,
                       J2_MATRIX_WEB_PAGE_FP,
                       J2_TRACEROUTE_WEB_PAGE_FP,
                       J2_EMAIL_TEMPLATE_FP)

    ps_trace.analysis(PREVIOUS_ROUTE_FP, HTML_DIR)

    if EMAIL_ALERTS and ps_trace.route_comparison.changed_routes:
        ps_trace.route_comparison.send_email_alert(EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, SMTP_SERVER)

    with open(DASHBOARD_WEB_PAGE_FP, "w") as web_matrix_file:
        current_time = datetime.datetime.now().strftime("%c")
        web_matrix = ps_trace.matrix.create_matrix_web_page(current_time, rdns_query)
        web_matrix_file.write(web_matrix)

    # Dictionary + file path for data_store, rdns and route_comparison
    data_to_save = ((ps_trace.force_graph, FORCE_GRAPH_DATA_FP),
                    (rdns, REVERSE_DNS_FP),
                    (ps_trace.route_comparison, PREVIOUS_ROUTE_FP))

    for objects, file_path in data_to_save:
        objects.save_as_json_file(file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("perfsonar_base", help="IP or base domain of the PerfSONAR MA")
    parser.add_argument("time_period", help="Time period (in seconds) from current point in time. "
                                            "e.g. 1 day == 86400", type=int)
    args = parser.parse_args()
    if args.time_period < TESTING_PERIOD:
        print("ERROR: Time period (%d seconds) is less than the traceroute testing period (%d seconds)."
              "\nExiting..." % (args.time_period, TESTING_PERIOD))
        exit()
    main(args.perfsonar_base, args.time_period)
