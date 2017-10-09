#!/usr/bin/python3
import argparse
import datetime
import os
import sys
import urllib.parse

from urllib.error import HTTPError

from classes import ForceGraph
from classes import Matrix
from classes import ReverseDNS
from classes import RouteComparison
from classes import Traceroute
from lib import json_loader_saver
from conf.email_configuration import ENABLE_EMAIL_ALERTS

TESTING_PERIOD = 1860

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

    ps_url = "https://%s/esmond/perfsonar/archive/?event-type=packet-trace&time-range=%s" % (ps_node_url, TESTING_PERIOD)
    traceroute_tests = json_loader_saver.retrieve_json_from_url(ps_url)

    data_list = []
    for singular_test in traceroute_tests:
            url = urllib.parse.urlsplit(singular_test['url'], scheme="https")
            api_key = "https://" + url.netloc + url.path + "packet-trace/base?time-range=" + str(test_time_range)
            data_list.append({'api': api_key,
                              'source': singular_test['source'],
                              'destination': singular_test["destination"]})

    return data_list


def latest_route_analysis(traceroute_test_data, traceroute_matrix, rdns_query):
    """
    Performs the current and historical analysis 
    :param traceroute_test_data: traceroute results
    :param traceroute_matrix: 
    :param rdns_query: 
    :return: 
    """
    traceroute = Traceroute.Traceroute(traceroute_test_data)

    source_ip = traceroute.source_ip
    destination_ip = traceroute.destination_ip

    traceroute.perform_traceroute_analysis()

    # Adds domain values to each hop within the traceroute.route_stats dictionary
    # due to object variable referencing
    for index, hop in enumerate(traceroute.route_stats):
        hop.update({"domain": rdns_query(hop['ip'])})

    traceroute.latest_trace_output()

    historical_routes = traceroute.historical_diff_routes()
    # Adds domain name to each route within historical routes
    if historical_routes:
        for historical_route in historical_routes:
            historical_route.update({"layer3_route": rdns_query(*historical_route["layer3_route"])})

    fp_html = "{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)
    # Replaces the colons(:) for IPv6 addresses to full-stops(.) to prevent file path issues when saving files on Win32
    if sys.platform == "win32":
        fp_html = fp_html.replace(":", ".")
    with open(os.path.join(HTML_DIR, fp_html), "w") as html_file:
        html_file.write(traceroute.create_traceroute_web_page(historical_routes, J2_TRACEROUTE_WEB_PAGE_FP))

    traceroute_rtt = traceroute.route_stats[-1]["rtt"]
    traceroute_matrix.update_matrix(source=source_ip, destination=destination_ip, rtt=traceroute_rtt, fp_html=fp_html)

    return traceroute.route_stats


def main(perfsonar_ma_url, time_period):
    traceroute_metadata = ''
    # Force Graph initialisation
    force_graph = ForceGraph.ForceGraph()

    rdns = ReverseDNS.ReverseDNS()
    # Loads reverse DNS information from a JSON file found at REVERSE_DNS_FP
    json_loader_saver.update_dictionary_from_json_file(rdns.rdns_store, REVERSE_DNS_FP)
    rdns_query = rdns.query

    route_comparison = RouteComparison.RouteComparison()
    # Loads previous route information from a JSON file found at PREVIOUS_ROUTE_FP
    json_loader_saver.update_dictionary_from_json_file(route_comparison.previous_routes, PREVIOUS_ROUTE_FP)
    route_compare = route_comparison.compare_and_update

    print("Acquiring traceroute tests... ", end="")
    try:
        traceroute_metadata = acquire_traceroute_tests(perfsonar_ma_url, test_time_range=time_period)
        print("%d test(s) received!" % len(traceroute_metadata))
    except HTTPError:
        print("Not a valid PerfSONAR Traceroute MA")
        exit()

    print("Creating Matrix.... ", end="")
    traceroute_matrix = Matrix.Matrix(traceroute_metadata)
    print("Matrix Created")

    # Computes the trace route data for all tests found within the perfSONAR MA
    for traceroute in traceroute_metadata:
        source, destination = traceroute["source"], traceroute["destination"]
        try:
            route_stats = latest_route_analysis(traceroute, traceroute_matrix, rdns_query)
        except HTTPError as e:
            print(e, "unable to retrieve traceroute data from %s" % (traceroute["api"]))
            print("Retrieving next test....")
            traceroute_matrix.update_matrix(source=source,
                                            destination=destination,
                                            rtt=False,
                                            fp_html=False)
            continue

        source_domain, destination_domain = rdns_query(source, destination)
        # Creates the hop list from the route_stats return
        route = [hop["domain"] for hop in route_stats]
        route_from_source = [source_domain] + route[:-1]
        # Creates force nodes between previous and current hop
        force_graph.create_force_nodes(route_stats, route_from_source, destination)
        # Compares current route with previous and stores current route in PREVIOUS_ROUTE_FP
        route_compare(source_domain, destination_domain, route)

    if ENABLE_EMAIL_ALERTS and route_comparison.email_contents:
        route_comparison.send_email_alert(J2_EMAIL_TEMPLATE_FP)

    with open(DASHBOARD_WEB_PAGE_FP, "w") as web_matrix_file:
        current_time = datetime.datetime.now().strftime("%c")
        web_matrix = traceroute_matrix.create_matrix_web_page(current_time, rdns_query, J2_MATRIX_WEB_PAGE_FP)
        web_matrix_file.write(web_matrix)

    # Dictionary + file path for force_graph, rdns and route_comparison
    dicts_to_save = ((force_graph.retrieve_graph(), FORCE_GRAPH_DATA_FP),
                     (rdns.rdns_store, REVERSE_DNS_FP),
                     (route_comparison.previous_routes, PREVIOUS_ROUTE_FP))

    for contents, file_path in dicts_to_save:
        json_loader_saver.save_dictionary_as_json_file(contents, file_path)


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
