import collections
import copy
import ipaddress
import itertools
import json
import socket
import os
import statistics
import time

import jinja2

from conf.email_configuration import EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, EMAIL_SERVER
from lib import email, json_loader_saver


class Jinja2Template:

    def __init__(self, jinja_template_file_path):
        self.jinja_template_fp = jinja_template_file_path

    def render_template_output(self, **template_variables):
        """
        Renders Jinja2 Templates with user submitted template variables
        :param template_variables: variables used within said template
        :type template_variables: str
        :return: rendered page or None if template could not be found
        """
        path, template_file = os.path.split(self.jinja_template_fp)
        # Sets path to current directory with "." if path variable is empty
        if not path:
            path = '.'
        template_loader = jinja2.FileSystemLoader(path)
        template_env = jinja2.Environment(loader=template_loader)
        try:
            template = template_env.get_template(template_file)
        except jinja2.exceptions.TemplateNotFound:
            print("Error: Unable to find Jinja2 template @ %s" % self.jinja_template_fp)
            return
        return template.render(template_variables)


class DataStore:

    def __init__(self):
        self.data_store = {}

    def update_from_json_file(self, file_path):
        """
        Updates dictionary with from a JSON file
        :param file_path: file path of the JSON file to load
        :return:
        """
        try:
            with open(file_path, "r") as file:
                self.data_store.update(json.load(fp=file))
        except FileNotFoundError:
            print("File %s not found!" % file_path)
        except ValueError:
            print("Error: Unable to update due to different dictionary_contents length")

    def save_as_json_file(self, file_path):
        """
        Saves the main data store in JSON format to the file path provided by file_path.
        :param file_path: file path of JSON to be saved
        :return: 
        """
        try:
            with open(file_path, "w") as file:
                json.dump(obj=self.data_store, fp=file, indent=4)
        except FileNotFoundError:
            print("Directory %s does not exist. File not saved!" % file_path)
        return

    def get_data(self):
        """
        :return: data dictionary
        """
        return self.data_store


class RouteComparison(DataStore, Jinja2Template):
    """
    Used for comparing two traceroute tests. If current route is different
     to the previous test, the new route will be saved and a HTML body
     comparing the two routes will be generated to be sent off as an HTML email.
    The class calls on the jinja_renderer function to load Jinja2 templates
     used for the email message and the email function to send said generated
     HTML email message.
    """
    def __init__(self, threshold, jinja_template_file_path):
        DataStore.__init__(self)
        Jinja2Template.__init__(self, jinja_template_file_path)
        self.email_contents = []
        self.threshold = threshold

    def compare_and_update(self, src_ip, dest_ip, route_stats):
        """
        Compares the current route with routes from when the previous test ran.
        If no previous routes are found, the current route will be appended to the
        data_store dictionary
        :param src_ip: Source IP address
        :type src_ip: str
        :param dest_ip: Destination IP address
        :type dest_ip: str
        :param route_stats: Current trace route list
        :type route_stats: list
        :return: None
        """
        stats = [{"domain": hop["domain"], "as": hop["as"], "rtt": hop["rtt"]} for hop in route_stats]
        try:
            previous = (hop["domain"] for hop in self.data_store[src_ip][dest_ip])
            current = (hop["domain"] for hop in route_stats)

            if self.comparison_check(previous, current):
                print("Route Changed")
                previous_route = self.data_store[src_ip][dest_ip]
                # Update current route into data_store dictionary to prevent update by reference
                self.data_store[src_ip][dest_ip] = copy.copy(stats)

                # Creates email body for routes that have changed
                self.email_contents.extend(["<h3>From %s to %s</h3>" % (src_ip, dest_ip)])
                self.email_contents.extend(self.__create_email_message(previous_route, stats))
        except KeyError:
            try:
                self.data_store[src_ip].update({dest_ip: stats})
            except KeyError:
                self.data_store.update({src_ip: {dest_ip: stats}})

    def comparison_check(self, list_a, list_b):
        """
        :param list_a:
        :param list_b:
        :return:
        """
        if not (list_a or list_b):
            raise ValueError
        if isinstance(list_a, int) or isinstance(list_b, int):
            raise TypeError
        if self.threshold > 1.0:
            raise ValueError

        combined_list = list(itertools.zip_longest(list_a, list_b))
        combined_list_length = len(combined_list)
        number_of_differences = len([i for i, j in combined_list if i != j])

        if number_of_differences / combined_list_length > self.threshold:
            return True

    @staticmethod
    def __create_email_message(previous_route, current_route):
        """
        Returns an HTML table str that compare the previous route with the current
        Example of the generated HTML message:
            From owamp-ps.singaren.net.sg to nsw-brwy-ps1.aarnet.net.au

                Hop:	Previous Route:              Current Route:
                1	et-1-0-0.singaren.net.sg	et-1-0-0.singaren.net.sg
                2	sin.aarnet.net.au	        sin.aarnet.net.au
                3	knsg.wa.aarnet.net.au	    d.syd.aarnet.net.au
                4	prka.sa.aarnet.net.au	    c.syd.aarnet.net.au
                5	eskp.nsw.aarnet.net.au	    be4.ta1.brwy.nsw.aarnet.net.au
                6	rsby.nsw.aarnet.net.au	    brwy.nsw.aarnet.net.au
                7	brwy.nsw.aarnet.net.au	    nsw-brwy-ps1.aarnet.net.au
                8	nsw-brwy-ps1.aarnet.net.au	*

        :param previous_route: Historical trace route
        :type previous_route: list
        :param current_route: Current trace route
        :type current_route: list
        :return html: list
        """
        # Adds "*" padding to the shortest route to ensure the current and previous route
        # are of equal length
        combined_route = itertools.zip_longest(previous_route,
                                               current_route,
                                               fillvalue={"domain": "*",
                                                          "as": "*",
                                                          "rtt": "*"})
        html = ["<table>\n<tr>"
                "<th>Hop:</th>"
                "<th>Previous Route:</th>"
                "<th>Previous RTT:</th>"
                "<th>Current Route:</th>"
                "<th>Current RTT:</th>"
                "</tr>"]
        for index, route in enumerate(combined_route):
            html.append("\n<tr>"
                        "<td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                        "</tr>" % (index + 1,
                                   route[0]["domain"],
                                   route[0]["rtt"],
                                   route[1]["domain"],
                                   route[1]["rtt"]))
        html.append("\n</table>")
        return html

    def send_email_alert(self):
        """
        Sends an email message to recipients regarding the routes that have changed

        Email example if using html_templates/email.html.j2:
            Dear Network Admin,

            The following routes have changed:
            From owamp-ps.singaren.net.sg to nsw-brwy-ps1.aarnet.net.au

            Hop:	Previous Route:              Current Route:
            1	et-1-0-0.singaren.net.sg	et-1-0-0.singaren.net.sg
            2	sin.aarnet.net.au	        sin.aarnet.net.au
            3	knsg.wa.aarnet.net.au	    d.syd.aarnet.net.au
            4	prka.sa.aarnet.net.au	    c.syd.aarnet.net.au
            5	eskp.nsw.aarnet.net.au	    be4.ta1.brwy.nsw.aarnet.net.au
            6	rsby.nsw.aarnet.net.au	    brwy.nsw.aarnet.net.au
            7	brwy.nsw.aarnet.net.au	    nsw-brwy-ps1.aarnet.net.au
            8	nsw-brwy-ps1.aarnet.net.au	*

            Kind regards,
            psTrace
        :return: None
        """
        email_body = "".join(self.email_contents)
        email_message = self.render_template_output(route_changes=email_body)
        email.send_mail(EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, email_message, EMAIL_SERVER)
        print("Notification email sent to %s" % ", ".join(EMAIL_TO))


class ReverseDNS(DataStore):
    """
    Performs reverse DNS Lookups on valid IP addresses and stores the IP address
    and its domain name within the data store. If the IP address has no domain name,
    the IP address will be stored with itself. Assumption is if an IP address does not
    have a domain, then it will be unlikely that it will in the future.
    """
    def __init__(self):
        DataStore.__init__(self)

    def query(self, *ip_addresses):
        """
        Performs a reverse DNS lookup on IP addresses by first looking through the
        data_store dictionary. If nothing is found within the said dictionary it will perform
        a query the DNS server.
        :param ip_addresses: IP Address to be queried
        :return: list; domain names of said IP addresses
        """
        ip_store = []
        for ip_address in ip_addresses:
            try:
                ipaddress.ip_address(ip_address)
                ip_store.append(self.data_store[ip_address])
            except ValueError:
                #print("Error: %s not a valid IP Address" % ip_address)
                ip_store.append(ip_address)
            except KeyError:
                self.data_store[ip_address] = self.__query_from_dns(ip_address)
                ip_store.append(self.data_store[ip_address])
        if len(ip_store) == 1:
            return ip_store[0]
        return ip_store

    @staticmethod
    def __query_from_dns(ip_address):
        """
        Queries the local DNS server for the domain name of the IP address
        :param ip_address: IP Address to be queried
        :return: Domain name or IP address depending if the lookup was successful
        """
        try:
            return socket.gethostbyaddr(ip_address)[0]
        except socket.gaierror:
            return ip_address
        except socket.herror:
            print("Unknown Host: %s" % ip_address)
            return ip_address


class Matrix(Jinja2Template):
    """
    Creates a matrix based on PerfSONAR Measurement Archive (MA) traceroute/path metadata
    and updates the matrix when traceroute information is received.
    The class calls on the jinja_renderer function to load Jinja2 templates
    to render the matrix web page from the template file once all of the
    matrix tests have been updated.
    """
    def __init__(self, test_metadata, jinja_template_file_path):
        """
        :param test_metadata: Metadata of all traceroute/path tests found within a PerfSOANR MA
        :type test_metadata: dict
        """
        Jinja2Template.__init__(self, jinja_template_file_path)
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
        source_ip_addresses = list({route_test['source'] for route_test in test_metadata})
        test_endpoints = list({route_test['destination'] for route_test in test_metadata})
        test_endpoints.extend(source_ip_addresses)
        self.endpoints = list(set(test_endpoints))
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

        return self.render_template_output(matrix=matrix_table, end_date=date_time)


class Traceroute(Jinja2Template):
    def __init__(self, traceroute_test_data, jinja_template_file_path):
        """
        :param traceroute_test_data: traceroute information gathered from the main perfSONAR query
        """
        Jinja2Template.__init__(self, jinja_template_file_path)
        self.route_stats = []
        self.different_route_index = set()

        self.source_ip = traceroute_test_data['source']
        self.destination_ip = traceroute_test_data['destination']
        self.trace_route_results = json_loader_saver.retrieve_json_from_url(traceroute_test_data['api'])
        self.latest_trace_route = self.trace_route_results[-1]
        self.end_date = self.datetime_from_timestamps(self.latest_trace_route["ts"])

    def __generate_hop_list(self, route_test):
        """
        Retrieves the traceroute from traceroute test index from self.trace_route_results[index]
        :param route_test: raw trace route test from self.trace_route_results[index]
        :return: trace route for traceroute_test
        """
        return [hop["ip"] if "ip" in hop else "null tag:%s_%d" % (self.destination_ip, index + 1)
                for (index, hop) in enumerate(route_test["val"])]

    @staticmethod
    def __retrieve_asn(ps_hop_dictionary):
        """
        Retrieves Autonomous System Numbers from a PerfSONAR hop details dictionary.
        ps_hop_dictionary example:
                                    {'ip': '192.168.0.1',
                                    'rtt': 0.1,
                                    'success': 1,
                                    'as': {'number': 00000, 'owner': 'LOCAL-AS'},
                                    'query': 1,
                                    'ttl': 1}
        :param ps_hop_dictionary: Dictionary containing hop details
        :return: as number
        """
        asn = "N/A"
        if "as" in ps_hop_dictionary:
            asn = ps_hop_dictionary["as"]["number"]
        return asn

    @staticmethod
    def datetime_from_timestamps(*timestamps):
        """
        :param timestamps:
        :return:
        """
        ts_store = [time.strftime("%c", time.localtime(int(ts))) for ts in timestamps]
        if len(ts_store) == 1:
            return ts_store[0]
        return ts_store

    @staticmethod
    def five_number_summary(number_list):
        """
        Finds the minimum, lower quartile (LQ), median, upper quartile (UQ) and maximum elements from a list of numbers.
        It also calculates the upper threshold based on the following equation:  threshold = UQ + 1.5 * (UQ - LQ)
        Return a dictionary containing the five number summary and threshold with the following key values:
            min, lower_quartile, median, upper_quartile, max, threshold
        :param number_list:
        :return:
        """
        number_list_size = len(number_list)
        try:
            number_list = sorted(number_list)
        except TypeError:
            print("Error: Invalid list elements found")
            return {"min": "", "lower_quartile": "", "median": "", "upper_quartile": "", "max": "", "threshold": ""}
        # Splits odd or even sized lists into their respective upper and lower sections
        # Odd sized list
        if number_list_size % 2:
            upper_index = int(number_list_size / 2) + 1
            lower_index = upper_index - 1
        else:
            upper_index = int(number_list_size / 2)
            lower_index = upper_index
        try:
            lower_quartile = statistics.median(number_list[:lower_index])
            upper_quartile = statistics.median(number_list[upper_index:])
            threshold = upper_quartile + 1.5 * (upper_quartile - lower_quartile)
            return {"min": number_list[0],
                    "lower_quartile": lower_quartile,
                    "median": statistics.median(number_list),
                    "upper_quartile": upper_quartile,
                    "max": number_list[-1],
                    "threshold": threshold}
        except TypeError:
            print("Error: Not int or float variables")
        except statistics.StatisticsError:
            print("Error: Not enough elements within list")
        return {"min": "", "lower_quartile": "", "median": "", "upper_quartile": "", "max": "", "threshold": ""}

    def retrieve_all_rtts_for_hop(self, hop_index, hop_ip):
        """
        Retrieves the round trip time values from every test if they satisfy the hop ip occurring
        at the specified hop index.
        It also detects different trace routes by capturing the test_index of failed hop_ip comparisons and for
        an IndexError.
        :param hop_index:
        :param hop_ip:
        :return:
        """
        rtt = []
        rtt_append = rtt.append
        different_route_add = self.different_route_index.add
        for (test_index, traceroute_test) in enumerate(self.trace_route_results):
            try:
                if traceroute_test["val"][hop_index]["ip"] == hop_ip:
                    rtt_append(float(traceroute_test["val"][hop_index]["rtt"]))
                else:
                    different_route_add(test_index)
            except (KeyError, IndexError):
                different_route_add(test_index)
                continue
        return rtt

    def perform_traceroute_analysis(self):
        """
        Performs latest_route_analysis on the most recent traceroute against previous traceroute test
        :return: route statistics for the most recent traceroute
        """
        # Retrieves latest route from self.trace_route_results
        hop_ip_list = self.__generate_hop_list(self.latest_trace_route)

        for (hop_index, current_hop_ip) in enumerate(hop_ip_list):
            # Goes through every test comparing the IP occurring at the same hop_index of the latest trace route
            rtt = []
            if "null tag:" not in current_hop_ip:
                rtt = self.retrieve_all_rtts_for_hop(hop_index=hop_index, hop_ip=current_hop_ip)

            hop_details = self.five_number_summary(rtt)
            # Save last value of the rtt as it is from the latest trace route; save empty value if rtt does not exist
            hop_details["rtt"] = round(rtt[-1], 2) if rtt else ""

            if len(rtt) > 1 and rtt:
                # rounds all hop_details to 2 d.p.s
                hop_details = {key: round(hop_details[key], 2)for key in hop_details}
                status = "warn" if hop_details["rtt"] > hop_details["threshold"] else "okay"
            elif len(rtt) == 1 and rtt:
                status = "unknown"
            else:
                hop_details["rtt"] = "unknown"
                status = "unknown"

            hop_details["status"] = status
            hop_details["ip"] = current_hop_ip
            hop_details["as"] = self.__retrieve_asn(self.latest_trace_route["val"][hop_index])

            self.route_stats.append(hop_details)
        return self.route_stats

    def historical_diff_routes(self):
        """
        Returns a list of different historical routes that occurred during the test period
        e.g.
        [{ts': timestamp1, 'layer3_route': [192.168.0.1, 192.168.0.254], 'as_route': ['N/A', 'N/A'], index: 2},
         {'ts': timestamp2, 'layer3_route': [192.168.1.4, 192.168.1.254], 'as_route': ['N/A', 'N/A'], index: 64}]
        :return: list
        """
        previous_route = ""
        historical_routes = []
        # Ends if no different routes were found at retrieve_all_rtts_for_hop during perform_traceroute_analysis call
        if not self.different_route_index:
            return
        # Reverse sort the different route index list as higher indexes indicate more recent dates
        sorted_diff_route_index = sorted(list(self.different_route_index), reverse=True)
        # Retrieves all of the different routes that occurred during the data period and stores the routes within the
        # historical_routes list
        for i in sorted_diff_route_index:
            route = self.__generate_hop_list(self.trace_route_results[i])
            asn = [self.__retrieve_asn(hop) for hop in self.trace_route_results[i]["val"]]

            if (i+1 not in sorted_diff_route_index) or (previous_route != route) or (i == 0):
                data = {'index': i,
                        'ts': self.datetime_from_timestamps(self.trace_route_results[i]["ts"]),
                        'layer3_route': route,
                        'as_route': asn}
                historical_routes.append(data)
            previous_route = route
        return historical_routes

    def latest_trace_output(self):
        """
        Prints out all of the current route with appropriate statistics
        :return: None
        """
        print("\nTraceroute to {ip}\n{end_date}\n".format(ip=self.destination_ip, end_date=self.end_date))
        print("Hop:\tIP:\t\t\tAS:   RTT: Min: Median: Threshold: Notice:\tDomain:\n")
        for (index, hop) in enumerate(self.route_stats):
            #print("{:4} {ip:24} {as:5} {rtt:6} {min:6} {median:6} {threshold:6} {status:7} {domain}".format(index + 1, **hop))
            print("{:4} {ip:24} {as:5} {rtt:6} {status:7} {domain}".format(index + 1, **hop))

    @staticmethod
    def __create_historical_route_html(historical_routes):
        """
        Creates HTML table for all historical routes found within historical_routes list
        e.g.
        [{ts': timestamp1, 'layer3_route': [192.168.0.1, 192.168.0.254], 'as_route': ['N/A', 'N/A'], index: 12},
         {'ts': timestamp2, 'layer3_route': [192.168.1.4, 192.168.1.254], 'as_route': ['N/A', 'N/A'], index: 2}]
        :param historical_routes: list containing all different historical routes
        :type historical_routes: list
        :return: HTML table of of all historical routes
        """
        html_historical = ["<h2>Historical Routes</h2>"]
        for h_route in historical_routes:
            html_historical.append("<p>{ts}</p>\n"
                                   "<table border='1'>\n"
                                   "<tr><td>Hop</td><td>Domain</td><td>ASN</td></tr>\n".format(ts=h_route["ts"]))

            for (index, hop) in enumerate(zip(h_route['layer3_route'], h_route['as_route'])):
                html_historical.append("<tr><td>%d</td><td>%s</td><td>%s</td></tr>\n" % (index + 1, hop[0], hop[1]))
            html_historical.append("</table>\n")
        return "".join(html_historical)

    def create_traceroute_web_page(self, historical_routes):
        """
        Creates a detailed HTML traceroute results page for the current traceroute test
        :param historical_routes:
        :return:
        """
        html_route = []
        html_historical = self.__create_historical_route_html(historical_routes) if historical_routes else ""

        for (index, hop_stats) in enumerate(self.route_stats):
            threshold = str(hop_stats["threshold"])
            if hop_stats["status"] == "warn":
                html_status = "&#10008; - WARN: Latency > " + threshold
            elif hop_stats["status"] == "okay":
                html_status = "&#10004; - OK"
            else:
                html_status = "&#10008; - UNKNOWN: " + threshold

            html_hop = ("<tr><td>{index}</td><td>{domain}</td><td>{ip}</td><td>{as}</td><td>{rtt}</td><td>{min}</td>"
                        "<td>{median}</td><td>{threshold}</td><td>{web_status}</td></tr>\n")
            html_route.append(html_hop.format(index=index + 1, web_status=html_status, **hop_stats))
        html_route = "".join(html_route)

        start_date = self.datetime_from_timestamps(self.trace_route_results[0]["ts"])

        return self.render_template_output(source_ip=self.source_ip,
                                           dest_ip=self.destination_ip,
                                           start_date=start_date,
                                           end_date=self.end_date,
                                           traceroute=html_route,
                                           historical=html_historical)


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

    def create_force_nodes(self, hop_details, previous_hop, destination_ip):
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
        if not isinstance(hop_details, list):
            hop_details = [hop_details]
        if not isinstance(previous_hop, list):
            previous_hop = [previous_hop]

        if len(hop_details) != len(previous_hop):
            print("Error: Hop information and previous hop list are of different length!")
            return

        for index, hop in enumerate(hop_details):
            node_point = ""
            if hop["ip"] == destination_ip:
                node_point = "destination"
            elif index == 0:
                node_point = "source"

            self.data_store.append({"source": previous_hop[index],
                                    "target": hop["domain"],
                                    "type": hop["status"],
                                    "node_point": node_point})
