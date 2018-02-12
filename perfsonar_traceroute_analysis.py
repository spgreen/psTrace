#!/usr/bin/python3
import argparse
import datetime
import os.path
import sys
import configparser
import urllib.parse

from urllib.error import HTTPError

import classes.PsTrace
from lib import json_loader_saver

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, 'config.ini'))

TESTING_PERIOD = int(config['PERFSONAR']['MAX_TIME_BETWEEN_TESTS'])
THRESHOLD = float(config['ROUTE_COMPARISON']['THRESHOLD'])
EMAIL_ALERTS = int(config['EMAIL']['ALERTS'])
EMAIL_TO = config['EMAIL']['TO'].replace(' ', '').split(',')
EMAIL_FROM = config['EMAIL']['FROM']
EMAIL_SUBJECT = config['EMAIL']['SUBJECT']
SMTP_SERVER = config['EMAIL']['SMTP_SERVER']

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


def acquire_traceroute_tests(ps_node_url, test_time_range=2400):
    """
    Acquires all recent traceroute results from a PerfSONAR Measurement Archive
    :param ps_node_url: either URL such without http(s):// or IP address. e.g. ps_ma.net.zz or 192.168.0.1
    :param test_time_range: time in seconds
    :return: 
    """
    if not isinstance(test_time_range, int):
        raise ValueError

    ps_url = "https://%s/esmond/perfsonar/archive/?event-type=packet-trace&time-range=%d" % (ps_node_url, TESTING_PERIOD)
    traceroute_tests = json_loader_saver.retrieve_json_from_url(ps_url)

    data_list = []
    for singular_test in traceroute_tests:
            url = urllib.parse.urlsplit(singular_test['url'], scheme="https")
            api_key = "https://{}{}packet-trace/base?time-range={}".format(
                url.netloc, url.path, test_time_range)
            data_list.append({'api': api_key,
                              'source': singular_test['source'],
                              'destination': singular_test["destination"]})

    return data_list


def latest_route_analysis(traceroute_test_data, traceroute_matrix):
    """
    Performs the current and historical analysis 
    :param traceroute_test_data: traceroute results
    :param traceroute_matrix:
    :return: 
    """
    traceroute = classes.PsTrace.Traceroute(traceroute_test_data, J2_TRACEROUTE_WEB_PAGE_FP)

    source_ip = traceroute.source_ip
    destination_ip = traceroute.destination_ip

    traceroute.perform_traceroute_analysis()
    traceroute.latest_trace_output()
    historical_routes = traceroute.historical_diff_routes()

    fp_html = "{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)
    # Replaces the colons(:) for IPv6 addresses with full-stops(.)
    # to prevent file path issues when saving on Win32
    if sys.platform == "win32":
        fp_html = fp_html.replace(":", ".")
    with open(os.path.join(HTML_DIR, fp_html), "w") as html_file:
        html_file.write(traceroute.create_traceroute_web_page(historical_routes))

    traceroute_rtt = traceroute.route_stats[-1]["rtt"]
    traceroute_matrix.update_matrix(source=source_ip, destination=destination_ip, rtt=traceroute_rtt, fp_html=fp_html)

    return traceroute.end_date, traceroute.route_stats


def main(perfsonar_ma_url, time_period):
    traceroute_metadata = ''
    # Force Graph initialisation
    force_graph = classes.PsTrace.ForceGraph()

    rdns = classes.PsTrace.ReverseDNS()
    # Loads reverse DNS information from a JSON file found at REVERSE_DNS_FP
    rdns.update_from_json_file(REVERSE_DNS_FP)
    rdns_query = rdns.query

    route_comparison = classes.PsTrace.RouteComparison(THRESHOLD, J2_EMAIL_TEMPLATE_FP)
    # Loads previous route information from a JSON file found at PREVIOUS_ROUTE_FP
    route_comparison.update_from_json_file(PREVIOUS_ROUTE_FP)
    route_compare = route_comparison.compare_and_update

    print("Acquiring traceroute tests... ", end="")

    try:
        traceroute_metadata = acquire_traceroute_tests(perfsonar_ma_url, test_time_range=time_period)
        print("%d test(s) received!" % len(traceroute_metadata))
    except HTTPError as e:
        print("%s - Unable to retrieve perfSONAR traceroute data from %s" % (e, perfsonar_ma_url))
        exit()

    print("Creating Matrix.... ", end="")
    traceroute_matrix = classes.PsTrace.Matrix(traceroute_metadata, J2_MATRIX_WEB_PAGE_FP)
    print("Matrix Created")

    # Computes the trace route data for all tests found within the perfSONAR MA
    for traceroute in traceroute_metadata:
        source_ip, destination_ip = traceroute.get("source"), traceroute.get("destination")
        source_domain, destination_domain = rdns_query(source_ip, destination_ip)
        try:
            time_of_test, route_stats = latest_route_analysis(traceroute, traceroute_matrix)
            current_traceroute_info = {"time": time_of_test,
                                       "source_ip": source_ip,
                                       "destination_ip": destination_ip,
                                       "source_domain": source_domain,
                                       "destination_domain": destination_domain,
                                       "route": route_stats}

        except HTTPError as e:
            print(e, "unable to retrieve traceroute data from %s" % traceroute.get("api"))
            print("Retrieving next test....")
            traceroute_matrix.update_matrix(source=source_ip,
                                            destination=destination_ip,
                                            rtt=False,
                                            fp_html=False)
            continue
        # Creates the hop list from the route_stats return
        route_from_source = [source_domain] + [hop["domain"] for hop in route_stats][:-1]
        # Creates force nodes between previous and current hop
        force_graph.create_force_nodes(route_stats, route_from_source, destination_ip)
        # Compares current route with previous and stores current route in PREVIOUS_ROUTE_FP
        route_compare(src_ip=source_ip, src_domain=source_domain,
                      dest_ip=destination_ip, dest_domain=destination_domain,
                      route_stats=route_stats, time_of_test=time_of_test)

    if EMAIL_ALERTS and route_comparison.changed_routes:
        route_comparison.send_email_alert(EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, SMTP_SERVER)

    with open(DASHBOARD_WEB_PAGE_FP, "w") as web_matrix_file:
        current_time = datetime.datetime.now().strftime("%c")
        web_matrix = traceroute_matrix.create_matrix_web_page(current_time, rdns_query)
        web_matrix_file.write(web_matrix)

    # Dictionary + file path for data_store, rdns and route_comparison
    data_to_save = ((force_graph, FORCE_GRAPH_DATA_FP),
                     (rdns, REVERSE_DNS_FP),
                     (route_comparison, PREVIOUS_ROUTE_FP))

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
