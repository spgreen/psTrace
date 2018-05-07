#!/usr/bin/python3
"""
TODO: Add Description
"""

import os.path
from classes.traceroute.comparison import RouteComparison
from classes.matrix import Matrix, ForceGraph

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


class PsTrace:
    def __init__(self, test_metadata, threshold, matrix_template_fp, web_template_fp, email_template_fp):
        """
        TODO: Add Description
        :param test_metadata:
        :param threshold:
        :param matrix_template_fp:
        :param web_template_fp:
        :param email_template_fp:
        """
        self.route_comparison = RouteComparison(threshold, email_template_fp)
        self.force_graph = ForceGraph()
        self.matrix = Matrix(test_metadata, matrix_template_fp, web_template_fp)

    def analysis(self, previous_routes_fp, html_save_directory):
        """
        TODO: Add Description
        :param previous_routes_fp:
        :param html_save_directory:
        :return:
        """
        self.route_comparison.update_from_json_file(previous_routes_fp)
        for traceroute in self.matrix.traceroutes:
            source_ip = traceroute.information['source_ip']
            destination_ip = traceroute.information['destination_ip']

            traceroute.perform_traceroute_analysis()
            traceroute.latest_trace_output()
            historical_routes = traceroute.historical_diff_routes()

            fp_html = "{source}-to-{dest}.html".format(source=source_ip, dest=destination_ip)
            # Replaces the colons(:) for IPv6 addresses with full-stops(.)
            # to prevent file path issues when saving on Win32
            fp_html = fp_html.replace(":", ".")
            with open(os.path.join(html_save_directory, fp_html), "w") as html_file:
                html_file.write(traceroute.create_traceroute_web_page(historical_routes))

            traceroute_rtt = traceroute.information['route_stats'][-1]["rtt"]
            self.matrix.update_matrix(source=source_ip,
                                      destination=destination_ip,
                                      rtt=traceroute_rtt,
                                      fp_html=fp_html)

            # Creates the hop list from the route_stats return
            route_from_source = [traceroute.information['source_domain']] + [hop["domain"] for hop in
                                                                             traceroute.information['route_stats']][:-1]
            # Creates force nodes between previous and current hop
            self.force_graph.create_force_nodes(traceroute.information['route_stats'],
                                                route_from_source,
                                                traceroute.information['source_ip'],
                                                traceroute.information['destination_ip'])
            # Compares current route with previous and stores current route in PREVIOUS_ROUTE_FP
            self.route_comparison.check_changes(traceroute.information)
