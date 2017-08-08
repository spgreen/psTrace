import collections

from lib import jinja_renderer


class Matrix:
    """
    Creates a matrix based on PerfSONAR Measurement Archive (MA) traceroute/path metadata 
    and updates the matrix when traceroute information is received.
    The class calls on the jinja_renderer function to load Jinja2 templates
    to render the matrix web page from the template file once all of the
    matrix tests have been updated.
    """
    def __init__(self, test_metadata):
        """
        :param test_metadata: Metadata of all traceroute/path tests found within a PerfSOANR MA
        :type test_metadata: dict
        """
        self.endpoints = None
        self.matrix = self.__creation(test_metadata)

    def __creation(self, test_metadata):
        """
        Creates the base matrix from the PerfSONAR MA traceroute/path metadata

        :param test_metadata: PerfSONAR MA trace route/path metadata for all tests within said MA
        :type test_metadata: dict
        :return: sorted matrix dictionary
        """
        # Retrieves all endpoint ip addresses from the the PerfSONAR MA metadata
        source_ip_addresses = list({route_test['source'] for route_test in test_metadata.values()})
        self.endpoints = list({route_test['destination'] for route_test in test_metadata.values()})
        self.endpoints.extend(source_ip_addresses)
        self.endpoints.sort()

        # Creates the destination information dict for all matrix sources to all destinations.
        matrix = {src: {dst: {"rtt": "", "fp_html": ""} for dst in self.endpoints} for src in source_ip_addresses}
        return self.sort_dictionary_by_key(matrix)

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

    def output(self):
        """
        :return: dict; current trace route matrix state
        """
        return self.matrix

    @staticmethod
    def sort_dictionary_by_key(unsorted_dictionary):
        """
        Sorts a dictionary object by its first key
        :param unsorted_dictionary: any vanilla dictionary
        :type unsorted_dictionary: dict
        :return: sorted dictionary by IP address
        """
        return collections.OrderedDict(sorted(unsorted_dictionary.items(), key=lambda i: i[0]))

    def create_matrix_web_page(self, date_time, rdns_query, jinja_template_fp):
        """
        Creates the matrix trace route HTML table and renders the complete web page
        from the Jinja2 template file plus the newly generated HTML table.

        :param date_time: Date and time of matrix creation. Create this here?
        :param rdns_query: rdns query function from ReverseDNS.py Class
        :param jinja_template_fp: File path of the Jinja2 template that will be used
        :return: Fully rendered Jinja2 Template string object
        """
        table_contents = []
        table_header = ["<tr><td>S/D</td>"]

        append_table_header = table_header.append
        append_table_contents = table_contents.append

        # Creates the HTML table header
        for endpoint in self.endpoints:
            append_table_header("<td><div><span>%s</span></div></td>" % rdns_query(endpoint))
        append_table_header("</tr>\n")

        # Create the matrix contents as a HTML table
        for source in self.matrix:
            append_table_contents("<tr><td>%s</td>" % rdns_query(source))
            for endpoint in self.endpoints:
                append_table_contents('<td><a href="{fp_html}">{rtt}</a></td>'
                                      .format(**self.matrix[source][endpoint]))
            append_table_contents("</tr>\n")

        matrix_table = "".join(table_header + table_contents)

        return jinja_renderer.render_template_output(jinja_template_fp,
                                                     matrix=matrix_table,
                                                     end_date=date_time)
