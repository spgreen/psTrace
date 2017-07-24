#!/usr/bin/python3
import sys
import datetime
import urllib.parse
import argparse

from classes import Matrix
from classes import ForceGraph
from classes import ReverseDNS
from classes import RouteComparison
from classes import Traceroute
from lib import json_loader_saver

EMAIL_TO = ["root@localhost"]
EMAIL_FROM = "pstrace@localhost"

REVERSE_DNS_FP = "json/rdns.json"
PREVIOUS_ROUTE_FP = "json/previous_routes.json"
FORCE_GRAPH_DATA_FP = "json/traceroute_force_graph.json"
DASHBOARD_WEB_PAGE_FP = "json/force.html"


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


def latest_route_analysis(test, traceroute_matrix, force_graph, rdns_query, previous_route_compare):
    """
    
    :param test: 
    :param traceroute_matrix: 
    :param force_graph: 
    :param rdns_query: 
    :return: 
    """
    traceroute = Traceroute.Traceroute(test)

    source_ip = traceroute.source_ip
    destination_ip = traceroute.destination_ip

    # Checks if test results exist after trying to retrieve traceroute test data from the perfSONAR MA
    if not traceroute.trace_route_results:
        print("Timeout receiving data from perfSONAR server\n Traceroute: %s to %s\n" % (source_ip, destination_ip))
        # Update Traceroute Matrix with timeout message
        traceroute_matrix.update(source=source_ip, destination=destination_ip)
        return
    elif len(traceroute.trace_route_results) <= 0:
        print("Error: Only 1 test available!")
        return

    traceroute.source_domain, traceroute.destination_domain = rdns_query(source_ip, destination_ip)

    traceroute.traceroute_analysis()

    # Retrieves the domain names for all IP address found within the traceroute test
    hop_domain_list = rdns_query(*traceroute.hop_ip_list)
    hop_domain_list_starting_at_source = [rdns_query(source_ip)] + hop_domain_list[:-1]
    # Adds domain values of each hop within the traceroute.route_stats dictionary due to object variable referencing
    [hop.update({"domain": hop_domain_list[index]}) for index, hop in enumerate(traceroute.route_stats)]

    # Checks and stores previous routes found within the traceroute test data
    previous_route_compare(traceroute.source_domain, traceroute.destination_domain, hop_domain_list)
    traceroute.latest_trace_output()

    historical_routes = traceroute.historical_diff_routes()
    # Adds domain name to each route within historical routes
    if historical_routes:
        [route.update({"route": rdns_query(*route["route"])}) for route in historical_routes]

    fp_html = "./html/{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)
    # Replaces the colons(:) for IPv6 addresses to full-stops(.) to prevent file path issues when saving files on Win32
    if sys.platform == "win32":
        fp_html = fp_html.replace(":", ".")
    with open(fp_html, "w") as html_file:
        html_file.write(traceroute.create_traceroute_web_page(historical_routes=historical_routes))

    traceroute_rtt = traceroute.route_stats[-1]["rtt"]
    traceroute_matrix.update_matrix(source=source_ip, destination=destination_ip, rtt=traceroute_rtt, fp_html=fp_html)

    # Creates force nodes between previous and current hop
    force_graph.create_force_nodes(traceroute.route_stats, hop_domain_list_starting_at_source, destination_ip)


def main(perfsonar_ma_url, time_period):
    tests = ''
    # Force Graph initialisation
    force_graph = ForceGraph.ForceGraph()

    rdns = ReverseDNS.ReverseDNS()
    json_loader_saver.update_dictionary_from_json_file(rdns.rdns_store, REVERSE_DNS_FP)
    rdns_query = rdns.query

    route_comparison = RouteComparison.RouteComparison()
    json_loader_saver.update_dictionary_from_json_file(route_comparison.previous_routes, PREVIOUS_ROUTE_FP)
    route_compare = route_comparison.compare_and_update

    print("Acquiring traceroute tests... ", end="")
    try:
        tests = acquire_traceroute_tests(perfsonar_ma_url, test_time_range=time_period)
        print("%d test(s) received!" % len(tests))
    except TypeError:
        print("Not a valid PerfSONAR Traceroute MA")
        exit()

    print("Creating Matrix.... ", end="")
    traceroute_matrix = Matrix.Matrix(tests)
    print("Matrix Created")

    # Computes the trace route data for all tests found within the perfSONAR MA
    [latest_route_analysis(test, traceroute_matrix, force_graph, rdns_query, route_compare) for test in tests.values()]

    if route_comparison.email_html:
        print("Notification email sent to %s" % ", ".join(EMAIL_TO))
        route_comparison.send_email_alert(email_to=EMAIL_TO, email_from=EMAIL_FROM)

    current_time = datetime.datetime.now().strftime("%c")
    web_matrix = traceroute_matrix.create_matrix_web_page(current_time, rdns_query)
    with open(DASHBOARD_WEB_PAGE_FP, "w") as web_matrix_file:
        web_matrix_file.write(web_matrix)

    # Dictionary + file path for force_graph, rdns and route_comparison
    dicts_to_save = ((force_graph.retrieve_graph(), FORCE_GRAPH_DATA_FP),
                     (rdns.rdns_store, REVERSE_DNS_FP),
                     (route_comparison.previous_routes, PREVIOUS_ROUTE_FP))

    [json_loader_saver.save_dictionary_as_json_file(i[0], i[1]) for i in dicts_to_save]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("perfsonar_base", help="IP or base domain of the PerfSONAR MA")
    parser.add_argument("time_period", help="Time period (in seconds) from current point in time. e.g. 1 day == 86400",
                        type=int)
    args = parser.parse_args()
    main(args.perfsonar_base, args.time_period)

