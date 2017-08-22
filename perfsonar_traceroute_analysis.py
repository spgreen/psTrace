#!/usr/bin/python3
import sys
import datetime
import urllib.parse
import argparse
import os

from classes import Matrix
from classes import ForceGraph
from classes import ReverseDNS
from classes import RouteComparison
from classes import Traceroute
from lib import json_loader_saver

EMAIL_TO = ["root@localhost"]
EMAIL_FROM = "pstrace@localhost"

HTML_DIR = "html"
JSON_DIR = "json"
TEMPLATE_DIR = "html_templates"

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

    :param ps_node_url: 
    :param test_time_range: 
    :return: 
    """
    ps_url = "https://" + ps_node_url + "/esmond/perfsonar/archive/?event-type=packet-trace&time-range=1200"
    traceroute_tests = json_loader_saver.retrieve_json_from_url(ps_url)

    data_dict = {}
    for singular_test in traceroute_tests:
        input_destination = singular_test['input-destination']
        if input_destination not in data_dict:
            url = urllib.parse.urlsplit(singular_test['url'], scheme="https")
            api_key = "https://" + url.netloc + url.path + "packet-trace/base?time-range=" + str(test_time_range)
            data_dict[input_destination] = {'api': api_key,
                                            'source': singular_test['source'],
                                            'destination': singular_test["destination"]}
    return data_dict


def latest_route_analysis(traceroute_test_data, traceroute_matrix, rdns_query):
    """
    
    :param traceroute_test_data: 
    :param traceroute_matrix: 
    :param force_graph: 
    :param rdns_query: 
    :return: 
    """
    traceroute = Traceroute.Traceroute(traceroute_test_data)

    source_ip = traceroute.source_ip
    destination_ip = traceroute.destination_ip

    # Checks if test results exist after trying to retrieve traceroute test data from the perfSONAR MA
    if len(traceroute.trace_route_results) <= 1:
        print("Error: Only 1 test available!")
        # TODO: Raise error for single tests
        return

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
            historical_route.update({"route": rdns_query(*historical_route["route"])})

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
    except urllib.error.HTTPError:
        print("Not a valid PerfSONAR Traceroute MA")
        exit()

    print("Creating Matrix.... ", end="")
    traceroute_matrix = Matrix.Matrix(traceroute_metadata)
    print("Matrix Created")

    # Computes the trace route data for all tests found within the perfSONAR MA
    for traceroute in traceroute_metadata.values():
        try:
            route_stats = latest_route_analysis(traceroute, traceroute_matrix, rdns_query)
        except urllib.error.HTTPError:
            print("Error: Unable to retrieve data. Retrieving next test....")
            traceroute_matrix.update_matrix(source=traceroute["source"],
                                            destination=traceroute["destination"],
                                            rtt=False,
                                            fp_html=False)
            continue

        source_domain, destination_domain = rdns_query(traceroute["source"], traceroute["destination"])
        # Creates the hop list from the route_stats return
        route = rdns_query(*[hop["ip"] for hop in route_stats])
        route_from_source = [source_domain] + route[:-1]
        # Creates force nodes between previous and current hop
        force_graph.create_force_nodes(route_stats, route_from_source, traceroute["destination"])
        # Checks and stores previous routes found within the traceroute test data
        route_compare(source_domain, destination_domain, route)

    if route_comparison.email_contents:
        print("Notification email sent to %s" % ", ".join(EMAIL_TO))
        route_comparison.send_email_alert(EMAIL_TO, EMAIL_FROM, J2_EMAIL_TEMPLATE_FP)

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
    parser.add_argument("time_period", help="Time period (in seconds) from current point in time. e.g. 1 day == 86400",
                        type=int)
    args = parser.parse_args()
    main(args.perfsonar_base, args.time_period)
