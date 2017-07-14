import collections
import json

from lib import jinja_renderer


class Matrix:
    def __init__(self, test_metadata):
        self.complete_matrix = self._creation(test_metadata)

    def _creation(self, test_metadata, src_node_key='source', dest_node_key='destination'):
        """
        
        :param test_metadata: 
        :param src_node_key: 
        :param dest_node_key: 
        :return: 
        """
        matrix = set()

        for singular_test in test_metadata:
            source_address = test_metadata[singular_test][src_node_key]
            destination_address = test_metadata[singular_test][dest_node_key]
            matrix.add(source_address)
            matrix.add(destination_address)

        # Changes set to a list to allow for indexing
        matrix_headers = list(matrix)
        # Creates the destination information dict for all matrix sources to all destinations - all values set to '*'.
        matrix_dict = {destination: {"rtt": "", "status": "", "fp_html": ""} for destination in matrix_headers}

        json_dumps = json.dumps
        json_loads = json.loads
        # Combines destination dictionary into the source dictionary creating the final matrix
        complete_matrix = {source: json_loads(json_dumps(matrix_dict)) for source in matrix}
        return self.sort_dict_by_key(complete_matrix)

    def update(self, source, destination, rtt, fp_html, status=""):
        """
        
        :param source: 
        :param destination: 
        :param rtt: 
        :param fp_html: 
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
            # update matrix with rtt value
            matrix = self.complete_matrix[source][destination]
            matrix["rtt"] = rtt
            matrix["status"] = status
            matrix["fp_html"] = fp_html

    def output(self):
        return self.complete_matrix

    @staticmethod
    def sort_dict_by_key(unsorted_dictionary):
        """Sorts an ordinary dictionary into a sorted ordered dictionary using the OrderedDict module 
            from the collections library"""
        return collections.OrderedDict(sorted(unsorted_dictionary.items(), key=lambda i: i[0]))

    def create_matrix_web_page(self, end_date, rdns_query, jinja_template_fp="html_templates/matrix.html.j2"):
        matrix_table = []
        table_header_contents = ""
        matrix_table_append = matrix_table.append
        for source in self.complete_matrix:
            # Since matrix is nxn we can use source as destination label
            table_header_contents += "<td><div><span>{destination}</span></div></td>".format(
                destination=rdns_query(source))
            matrix_table_append("<tr><td>{source}</td>".format(source=rdns_query(source)))

            for destination in self.complete_matrix:
                trace = self.complete_matrix[source][destination]
                matrix_table_append('<td id="{status}"><a href=".{fp_html}">{rtt}</a></td>'.format(**trace))
            matrix_table_append("</tr>\n")

        matrix_table = "<tr><td>S/D</td>{header}</tr>\n".format(header=table_header_contents) + "".join(matrix_table)
        return jinja_renderer.render_template_output(jinja_template_fp, matrix=matrix_table, end_date=end_date)
