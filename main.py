import json
import timeit
from classes import Matrix
from classes.Traceroute import Traceroute
from lib import html_traceroute
from lib import reverse_dns, AcquireTracerouteTestAPI


def create_force_nodes(hop_details, previous_hop, destination_ip):
    """
    
    :param hop_details: 
    :param previous_hop: 
    :param destination_ip: 
    :return: 
    """
    value = "end" if hop_details[1]["ip"] == destination_ip else "null"
    size = 15 if hop_details[0] == 0 else 7

    return {"source": previous_hop,
            "target": hop_details[1]["domain"],
            "type": hop_details[1]["status"],
            "size": size,
            "value": value}


def latest_route_analysis(test, traceroute_matrix, force_graph, rdns):
    """
    
    :param test: 
    :param traceroute_matrix: 
    :param force_graph: 
    :param rdns: 
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
        traceroute_matrix.update(source=traceroute.source_ip,
                                 destination=traceroute.destination_ip)
        print(traceroute_matrix.complete_matrix)
        return

    elif len(traceroute.test_results) <= 0:
        print("Error: Only 1 test available!")
        return

    traceroute.traceroute_analysis(rdns)
    traceroute.latest_trace_output()

    historical_routes = traceroute.historical_diff_routes()
    traceroute_web_page = html_traceroute.create_html_traceroute_page(route_stats=traceroute.route_stats,
                                                                      source_ip=source_ip,
                                                                      destination_ip=destination_ip,
                                                                      start_date=traceroute.start_date,
                                                                      end_date=traceroute.end_date,
                                                                      historical_routes=historical_routes)

    fp_html = "./html/{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)
    # Replaces the colons(:) for IPv6 addresses to full-stops(.) to prevent file path issues when saving files
    if ":" in fp_html:
        return fp_html.replace(":", ".")

    traceroute_matrix.update(source=source_ip,
                             destination=destination_ip,
                             rtt=traceroute.route_stats[-1]["rtt"],
                             fp_html=fp_html)

    with open(fp_html, "w") as html_file:
        html_file.write(traceroute_web_page)

    # Creates force nodes between previous and current hop
    hop_domain_list_starting_at_source = [source_ip] + [hop["domain"] for hop in traceroute.route_stats]

    force_graph += list(map(lambda x, y: create_force_nodes(x, y, destination_ip),
                            enumerate(traceroute.route_stats), hop_domain_list_starting_at_source))

    return force_graph


def main():
    # Force Graph initialisation
    force_graph = []

    rdns = reverse_dns.load_rdns_table("json/rdns.json")

    print("Acquiring traceroute tests...")
    tests = AcquireTracerouteTestAPI.acquire_traceroute_tests("perfsonar_base_url")
    print("%d test(s) received!" % len(tests))

    print("Creating Matrix....")
    traceroute_matrix = Matrix.Matrix(tests)
    print("Matrix Created")

    for test in tests:
        force_graph = latest_route_analysis(tests[test], traceroute_matrix, force_graph, rdns)

    web_matrix = html_traceroute.create_matrix(traceroute_matrix.complete_matrix, "end date", rdns)
    with open("./json/force.html", "w") as web_matrix_file:
        web_matrix_file.write(web_matrix)

    with open("./json/traceroute_force_graph.json", "w") as force_graph_file:
        json.dump(force_graph, fp=force_graph_file, indent=4)

if __name__ == '__main__':
    print(timeit.timeit("main()", setup="from __main__ import main", number=1) / 1)
    #main()