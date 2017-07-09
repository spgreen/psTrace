import json
import timeit
from classes import Matrix
from classes import ForceGraph
from classes import ReverseDNS
from classes.Traceroute import Traceroute
from lib import html_traceroute
from lib import AcquireTracerouteTestAPI


def latest_route_analysis(test, traceroute_matrix, force_graph, rdns_query):
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

    # Place within class error checks
    if not traceroute.test_results:
        print("Timeout receiving data from perfSONAR server\n Traceroute: %s to %s\n" %
              (traceroute.source_ip,
               traceroute.destination_ip))

        """Update Matrix with timeout"""
        traceroute_matrix.update(source=traceroute.source_ip, destination=traceroute.destination_ip)
        print(traceroute_matrix.complete_matrix)
        return

    elif len(traceroute.test_results) <= 0:
        print("Error: Only 1 test available!")
        return

    traceroute.traceroute_analysis()

    hop_domain = list(map(lambda x: rdns_query(x), [hop["ip"] for hop in traceroute.route_stats]))
    hop_domain_list_starting_at_source = [rdns_query(source_ip)] + hop_domain[:-1]
    # Adds IP domain values of each within the traceroute.route_stats dictionary due to object variable referencing
    [hop.update({"domain": hop_domain[index]}) for index, hop in enumerate(traceroute.route_stats)]

    traceroute.latest_trace_output()

    historical_routes = traceroute.historical_diff_routes()
    # Adds domain name to historical routes
    if historical_routes:
        for route in historical_routes:
            ip_domain_list = list(map(lambda x: rdns_query(x), route["route"]))
            route.update({"route": ip_domain_list})

    traceroute_web_page = html_traceroute.create_html_traceroute_page(route_stats=traceroute.route_stats,
                                                                      source_ip=source_ip,
                                                                      destination_ip=destination_ip,
                                                                      start_date=traceroute.start_date,
                                                                      end_date=traceroute.end_date,
                                                                      historical_routes=historical_routes)

    fp_html = "./html/{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)
    # Replaces the colons(:) for IPv6 addresses to full-stops(.) to prevent file path issues when saving files
    if ":" in fp_html:
        fp_html.replace(":", ".")

    traceroute_matrix.update(source=source_ip,
                             destination=destination_ip,
                             rtt=traceroute.route_stats[-1]["rtt"],
                             fp_html=fp_html)

    with open(fp_html, "w") as html_file:
        html_file.write(traceroute_web_page)

    # Creates force nodes between previous and current hop
    list(map(lambda x, y: force_graph.create_force_nodes(x, y, destination_ip),
             enumerate(traceroute.route_stats), hop_domain_list_starting_at_source))


def main():
    rdns_fp = "json/rdns.json"

    # Force Graph initialisation
    force_graph = ForceGraph.ForceGraph()

    rdns = ReverseDNS.ReverseDNS()
    rdns.load_reverse_dns_json_file(rdns_fp)
    rdns_query = rdns.query
    print("Acquiring traceroute tests...")
    tests = AcquireTracerouteTestAPI.acquire_traceroute_tests("perfsonar MA URL", test_time_range=604800)
    print("%d test(s) received!" % len(tests))

    print("Creating Matrix....")
    traceroute_matrix = Matrix.Matrix(tests)
    print("Matrix Created")

    # Computes the trace route data for all tests found within the perfSONAR MA
    [latest_route_analysis(test, traceroute_matrix, force_graph, rdns_query) for test in tests.values()]

    web_matrix = html_traceroute.create_matrix(traceroute_matrix.complete_matrix, "end date", rdns_query)
    with open("./json/force.html", "w") as web_matrix_file:
        web_matrix_file.write(web_matrix)

    with open("./json/traceroute_force_graph.json", "w") as force_graph_file:
        json.dump(force_graph.retrieve_graph(), fp=force_graph_file, indent=4)

    rdns.save_reverse_dns_json_file(rdns_fp)


if __name__ == '__main__':
    print(timeit.timeit("main()", setup="from __main__ import main", number=1) / 1)
    # main()
