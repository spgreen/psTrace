#!/usr/bin/python3
"""
TODO: Add Description
"""

import collections
import ipaddress
from urllib.error import HTTPError
from classes.base import Jinja2Template, DataStore
from classes.traceroute.analysis import TracerouteAnalysis

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


class Matrix(Jinja2Template):
    """
    Creates a matrix based on PerfSONAR Measurement Archive (MA) traceroute/path metadata
    and updates the matrix when traceroute information is received.
    The class calls on the jinja_renderer function to load Jinja2 templates
    to render the matrix web page from the template file once all of the
    matrix tests have been updated.
    """
    def __init__(self, test_metadata, jinja_template_file_path, web_jinja2_template_fp):
        """
        Initialises the traceroute matrix dashboard and prepares each traceroute found within the matrix
        for analysis
        :param test_metadata: Metadata of all traceroute/path tests found within a PerfSOANR MA
        :param jinja_template_file_path: Matrix HTML Jinja2 template file path
        :param web_jinja2_template_fp: Traceroute HTML Jinja2 template file path
        """
        Jinja2Template.__init__(self, jinja_template_file_path)
        self.endpoints = None
        self.matrix = self.__creation(test_metadata)

        def traceroutes_generator():
            for traceroute in test_metadata:
                try:
                    yield TracerouteAnalysis(traceroute, web_jinja2_template_fp)
                except HTTPError as e:
                    print(e, "unable to retrieve traceroute data from %s" % traceroute.get("api"))
                    print("Retrieving next test....")
                    self.update_matrix(source=traceroute.get('source'),
                                       destination=traceroute.get('destination'),
                                       rtt=False,
                                       fp_html=False)
                    continue

        self.traceroutes = traceroutes_generator()

    def __creation(self, test_metadata):
        """
        Creates the base matrix from the PerfSONAR MA traceroute/path metadata

        :param test_metadata: PerfSONAR MA trace route/path metadata for all tests within said MA
        :type test_metadata: dict
        :return: sorted matrix dictionary
        """
        # Retrieves all endpoint ip addresses from the the PerfSONAR MA metadata
        source_ip_addresses = list({route_test['source'] for route_test in test_metadata})
        test_endpoints = list({route_test['destination'] for route_test in test_metadata})
        test_endpoints.extend(source_ip_addresses)
        self.endpoints = list(set(test_endpoints))
        self.endpoints.sort()

        # Creates the destination information dict for all matrix sources to all destinations.
        matrix = {src: {dst: {"rtt": "", "fp_html": ""} for dst in self.endpoints} for src in source_ip_addresses}
        return collections.OrderedDict(sorted(matrix.items(), key=lambda i: i[0]))

    def update_matrix(self, source, destination, rtt, fp_html):
        """
        Updates matrix with trace route round-trip times, html file path
        and status for the specific test

        :param source: Source IP address
        :param destination: Destination IP address
        :param rtt: Round trip time to the destination IP address
        :param fp_html: File path of the HTML file containing a detailed view of the specific test
        :return: None
        """
        if not rtt:
            self.matrix[source][destination]["rtt"] = "psTimeout"
            return self.matrix

        elif source not in self.matrix.keys():
            # Used to include sources not found from the initial query"""
            return

        if not self.matrix[source][destination]["rtt"]:
            self.matrix[source][destination].update({"rtt": rtt, "fp_html": fp_html})
        return

    def output(self):
        """
        :return: dict; current trace route matrix state
        """
        return self.matrix

    def create_matrix_web_page(self, date_time, rdns_query):
        """
        Creates the matrix trace route HTML table and renders the complete web page
        from the Jinja2 template file plus the newly generated HTML table.

        :param date_time: Date and time of matrix creation. Create this here?
        :param rdns_query: rdns query function from ReverseDNS.py Class
        :return: Fully rendered Jinja2 Template string object
        """
        table_contents = []
        table_header = ["<tr><td>S/D</td>"]

        append_table_header = table_header.append
        append_table_contents = table_contents.append
        # Creates the HTML table header
        for endpoint in self.endpoints:
            label = self._matrix_header_label(endpoint, rdns_query(endpoint))
            append_table_header("<td><div><span>%s</span></div></td>" % label)
        append_table_header("</tr>\n")

        # Create the matrix contents as a HTML table
        for source in self.matrix:
            label = self._matrix_header_label(source, rdns_query(source))
            append_table_contents("<tr><td>%s</td>" % label)
            for endpoint in self.endpoints:
                append_table_contents('<td><a href="{fp_html}">{rtt}</a></td>'
                                      .format(**self.matrix[source][endpoint]))
            append_table_contents("</tr>\n")

        matrix_table = "".join(table_header + table_contents)

        return self.render_template_output(matrix=matrix_table, end_date=date_time)

    @staticmethod
    def _matrix_header_label(ip, domain):
        """
        Returns a domain name with IPv6 tagged to the end if the IP address is IPv6 otherwise it
        returns just the domain name.
        :param ip: IP Address
        :param domain: Domain name address
        :return: str
        """
        ip_version = ipaddress.ip_address(ip).version
        return " ".join([domain, '(IPv6)']) if ip_version is 6 else domain


class ForceGraph(DataStore):
    """
    Creates the data required for the D3.js Force Graph used within  the matrix.html.j2 template.
    It saves each hop and its information as a dict which is then appended to the force graph list.
    Force graph list example:
        [
            {
                "target": "et-1-0-0.singaren.net.sg",
                "source": "owamp.singaren.net.sg",
                "node_point": "source",
                "type": "okay"
            },
            {
                "target": "sg-mx60.jp.apan.net",
                "source": "et-1-0-0.singaren.net.sg",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "hk-mx60.jp.apan.net",
                "source": "sg-mx60.jp.apan.net",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "cuhk.hkix.net",
                "source": "hk-mx60.jp.apan.net",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "et-0-2-1-cuhk.hkix.net",
                "source": "cuhk.hkix.net",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "ps1.cuhk.edu.hk",
                "source": "et-0-2-1-cuhk.hkix.net",
                "node_point": "destination",
                "type": "okay"
            }
        ]
    """
    def __init__(self):
        """
        Initialises the list for storing force graph dictionaries used for D3.js
        found within the matrix.html.j2 template.
        """
        DataStore.__init__(self)
        self.data_store = []

    def update_from_json_file(self, file_path):
        """
        :param file_path:
        :return:
        """
        raise AttributeError("'ForceGraph' object has no attribute 'update_from_json_file'")

    def create_force_nodes(self, hop_details, previous_hop, source_ip, destination_ip):
        """
        Creates a force node dictionary entry which will be appended to the force graph list.
        Example dictionary:
            {
                "target": "et-1-0-0.singaren.net.sg",
                "source": "owamp.singaren.net.sg",
                "node_point": "source",
                "type": "okay"
            }

        :param hop_details: Nested dictionary in list or single dict of trace route hop information
        :type hop_details: list or dict
        :param previous_hop: Singular entry or list. If list it will be the route starting
                             at the source ip
        :type previous_hop: list or str
        :param destination_ip: Trace route destination IP address
        :type destination_ip: str
        :return: None
        """
        if len(hop_details) != len(previous_hop):
            print("Error: Hop information and previous hop list are of different length!")
            return

        unique_tag = 'null tag:{index}_%s_%s' %(source_ip, destination_ip)
        for index, hop in enumerate(hop_details):
            node_point = ""
            if hop.get("ip") == destination_ip:
                node_point = "destination"
            elif index == 0:
                node_point = "source"

            source = unique_tag.format(index=index) if '*' in previous_hop[index] else previous_hop[index]
            target = hop.get('hostname', unique_tag.format(index=index+1))
            self.data_store.append({"source": source,
                                    "target": target,
                                    "type": hop["status"],
                                    "node_point": node_point})
