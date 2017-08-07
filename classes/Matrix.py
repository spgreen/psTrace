import collections

from lib import jinja_renderer


class Matrix:
    def __init__(self, test_metadata):
        self.complete_matrix = self.__creation(test_metadata)

    def __creation(self, route_tests):
        """
        Creates the base traceroute matrix from PerfSONAR MA data 
        :param route_tests: 
        :return: 
        """
        endpoints = set()
        # Retrieves all destination and source ip addresses for the traceroute tests received from the perfsonar MA
        [endpoints.update([route_test['source'], route_test['destination']]) for route_test in route_tests.values()]
        matrix_list = list(endpoints)
        # Creates the destination information dict for all matrix sources to all destinations -.
        matrix = {src: {dest: {"rtt": "", "status": "", "fp_html": ""} for dest in matrix_list} for src in matrix_list}
        return self.sort_dictionary_by_key(matrix)

    def update_matrix(self, source, destination, rtt, fp_html, status=""):
        """
        Updates matrix with trace route round-trip times, html file path and status for the specific test
        :param source: Source IP address
        :param destination: Destination IP address
        :param rtt: Round trip time to the destination IP address 
        :param fp_html: File path of the HTML file containing a detailed view of the specific test
        :param status: 
        :return: 
        """
        if not rtt:
            self.complete_matrix[source][destination]["rtt"] = "psTimeout"
            return self.complete_matrix

        elif source not in self.complete_matrix.keys():
            # Used to include sources not found from the initial query"""
            return

        if not self.complete_matrix[source][destination]["rtt"]:
            self.complete_matrix[source][destination].update({"rtt": rtt, "status": status, "fp_html": fp_html})

    def output(self):
        return self.complete_matrix

    @staticmethod
    def sort_dictionary_by_key(unsorted_dictionary):
        # Sorts an ordinary dictionary into a sorted ordered dictionary by IP address key
        return collections.OrderedDict(sorted(unsorted_dictionary.items(), key=lambda i: i[0]))

    def create_matrix_web_page(self, end_date, rdns_query, jinja_template_fp):
        """
        Creates the matrix traceroute HTML table and renders the complete matrix web page from the Jinja2 template file
        :param end_date: 
        :param rdns_query: 
        :param jinja_template_fp: 
        :return: 
        """
        table_contents = []
        table_header = ["<tr><td>S/D</td>"]

        table_header_append = table_header.append
        table_contents_append = table_contents.append

        # Formats the complete matrix into an HTML table
        for source in self.complete_matrix:
            # Since matrix is nxn we can use source as destination label
            domain_address = rdns_query(source)
            table_header_append("<td><div><span>{dest}</span></div></td>".format(dest=domain_address))
            table_contents_append("<tr><td>{source}</td>".format(source=domain_address))
            for destination in self.complete_matrix:
                trace = self.complete_matrix[source][destination]
                table_contents_append('<td id="{status}"><a href="{fp_html}">{rtt}</a></td>'.format(**trace))
            table_contents_append("</tr>\n")
        table_header_append("</tr>\n")

        matrix_table = "".join(table_header + table_contents)

        return jinja_renderer.render_template_output(jinja_template_fp, matrix=matrix_table, end_date=end_date)
