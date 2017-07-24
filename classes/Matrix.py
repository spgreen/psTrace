import collections
import json

from lib import jinja_renderer


class Matrix:
    def __init__(self, test_metadata):
        self.complete_matrix = self.__creation(test_metadata)

    def __creation(self, test_metadata, src_node_key='source', dest_node_key='destination'):
        """
        Creates the base traceroute matrix from PerfSONAR MA data 
        :param test_metadata: 
        :param src_node_key: 
        :param dest_node_key: 
        :return: 
        """
        matrix = set()

        # Update matrix with source and destination addresses for each test
        for singular_test in test_metadata.values():
            matrix.update([singular_test[src_node_key], singular_test[dest_node_key]])

        # Creates the destination information dict for all matrix sources to all destinations - all values set to '*'.
        matrix_dict = {destination: {"rtt": "", "status": "", "fp_html": ""} for destination in list(matrix)}

        json_dumps, json_loads = json.dumps, json.loads
        # Combines destination dictionary into the source dictionary creating the final matrix
        complete_matrix = {source: json_loads(json_dumps(matrix_dict)) for source in matrix}
        return self.sort_dict_by_key(complete_matrix)

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
    def sort_dict_by_key(unsorted_dictionary):
        # Sorts an ordinary dictionary into a sorted ordered dictionary by IP address key
        return collections.OrderedDict(sorted(unsorted_dictionary.items(), key=lambda i: i[0]))

    def create_matrix_web_page(self, end_date, rdns_query, jinja_template_fp="html_templates/matrix.html.j2"):
        """
        
        :param end_date: 
        :param rdns_query: 
        :param jinja_template_fp: 
        :return: 
        """
        table_contents = []
        table_header = ["<tr><td>S/D</td>"]

        table_header_append = table_header.append
        table_contents_append = table_contents.append

        for source in self.complete_matrix:
            # Since matrix is nxn we can use source as destination label
            domain_address = rdns_query(source)
            table_header_append("<td><div><span>{dest}</span></div></td>".format(dest=domain_address))
            table_contents_append("<tr><td>{source}</td>".format(source=domain_address))
            # Fills the table with test data
            for destination in self.complete_matrix:
                trace = self.complete_matrix[source][destination]
                table_contents_append('<td id="{status}"><a href=".{fp_html}">{rtt}</a></td>'.format(**trace))
            table_contents_append("</tr>\n")
        table_header_append("</tr>\n")

        matrix_table = "".join(table_header + table_contents)

        return jinja_renderer.render_template_output(jinja_template_fp, matrix=matrix_table, end_date=end_date)
