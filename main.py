import sys
import datetime

from classes import Matrix
from classes import ForceGraph
from classes import ReverseDNS
from classes import RouteComparison
from classes.Traceroute import Traceroute
from lib import acquire_traceroute_test_from_api
from lib import json_loader_saver


def latest_route_analysis(test, traceroute_matrix, force_graph, rdns_query, previous_route_compare):
    """
    
    :param test: 
    :param traceroute_matrix: 
    :param force_graph: 
    :param rdns_query: 
    :return: 
    """
    traceroute = Traceroute(test)
    source_ip = traceroute.source_ip
    destination_ip = traceroute.destination_ip

    traceroute.source_domain = rdns_query(source_ip)
    traceroute.destination_domain = rdns_query(destination_ip)

    # Place within class error checks
    if not traceroute.test_results:
        print("Timeout receiving data from perfSONAR server\n Traceroute: %s to %s\n" % (source_ip, destination_ip))
        # Update Matrix with timeout
        traceroute_matrix.update(source=source_ip, destination=destination_ip)
        return
    elif len(traceroute.test_results) <= 0:
        print("Error: Only 1 test available!")
        return

    traceroute.traceroute_analysis()

    hop_domain_list = list(map(lambda x: rdns_query(x), [hop["ip"] for hop in traceroute.route_stats]))
    hop_domain_list_starting_at_source = [rdns_query(source_ip)] + hop_domain_list[:-1]
    # Adds IP domain values of each within the traceroute.route_stats dictionary due to object variable referencing
    [hop.update({"domain": hop_domain_list[index]}) for index, hop in enumerate(traceroute.route_stats)]

    previous_route_compare(traceroute.source_domain, traceroute.destination_domain, hop_domain_list)
    traceroute.latest_trace_output()

    historical_routes = traceroute.historical_diff_routes()

    # Adds domain name to each route within historical routes
    if historical_routes:
        [route.update({"route": list(map(lambda x: rdns_query(x), route["route"]))}) for route in historical_routes]

    fp_html = "./html/{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)

    # Replaces the colons(:) for IPv6 addresses to full-stops(.) to prevent file path issues when saving files on Win32
    if sys.platform == "win32":
        fp_html = fp_html.replace(":", ".")

    with open(fp_html, "w") as html_file:
        html_file.write(traceroute.create_traceroute_web_page(historical_routes=historical_routes))

    traceroute_rtt = traceroute.route_stats[-1]["rtt"]
    traceroute_matrix.update(source=source_ip, destination=destination_ip, rtt=traceroute_rtt, fp_html=fp_html)

    # Creates force nodes between previous and current hop
    list(map(lambda x, y: force_graph.create_force_nodes(x, y, destination_ip),
             enumerate(traceroute.route_stats), hop_domain_list_starting_at_source))


def main(perfsonar_ma_url, time_period):
    rdns_fp = "json/rdns.json"
    previous_routes_fp = "json/previous_routes.json"
    force_graph_fp = "json/traceroute_force_graph.json"
    tests = ""

    # Force Graph initialisation
    force_graph = ForceGraph.ForceGraph()

    rdns = ReverseDNS.ReverseDNS()
    json_loader_saver.update_dictionary_from_json_file(rdns.rdns_store, rdns_fp)
    rdns_query = rdns.query

    route_comparison = RouteComparison.RouteComparison()
    json_loader_saver.update_dictionary_from_json_file(route_comparison.previous_routes, previous_routes_fp)
    route_compare = route_comparison.compare_and_update

    print("Acquiring traceroute tests... ", end="")
    try:
        tests = acquire_traceroute_test_from_api.acquire_traceroute_tests(perfsonar_ma_url, test_time_range=time_period)
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
        print("Notification email sent!")
        route_comparison.send_email_alert(email_to=["root@localhost"], email_from="pstrace@localhost")

    current_time = datetime.datetime.now().strftime("%c")
    web_matrix = traceroute_matrix.create_matrix_web_page(current_time, rdns_query)
    with open("./json/force.html", "w") as web_matrix_file:
        web_matrix_file.write(web_matrix)

    # Dictionary + file path for force_graph, rdns and route_comparison
    dicts_to_save = ((force_graph.retrieve_graph(), force_graph_fp),
                     (rdns.rdns_store, rdns_fp),
                     (route_comparison.previous_routes, previous_routes_fp))

    [json_loader_saver.save_dictionary_as_json_file(i[0], i[1]) for i in dicts_to_save]


if __name__ == '__main__':
    #print(timeit.timeit("main()", setup="from __main__ import main", number=1) / 1)
    main(sys.argv[1], sys.argv[2])

