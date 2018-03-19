import collections
import ipaddress
import itertools
import json
import socket
import os.path
import statistics
import time
from urllib.error import HTTPError

import jinja2

from lib import email, json_loader_saver


class Jinja2Template:

    def __init__(self, jinja_template_file_path):
        self.jinja_template_fp = jinja_template_file_path

    def render_template_output(self, **template_variables):
        """
        Renders Jinja2 Templates with user submitted template variables
        :param template_variables: variables used within said template
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


class PsTrace:
    def __init__(self, test_metadata, threshold, matrix_template_fp, web_template_fp, email_template_fp):
        """

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
                                                traceroute.information['destination_ip'])
            # Compares current route with previous and stores current route in PREVIOUS_ROUTE_FP
            self.route_comparison.compare_and_update(**traceroute.information)


class RouteComparison(DataStore, Jinja2Template):
    """
    Used for comparing two traceroute tests. If current route is different
     to the previous test, the new route will be saved and a HTML body
     comparing the two routes will be generated to be sent off as an HTML email.
    The class calls on the jinja_renderer function to load Jinja2 templates
     used for the email message and the email function to send said generated
     HTML email message.
    """
    changed_routes = []

    def __init__(self, threshold, jinja_template_file_path):
        DataStore.__init__(self)
        Jinja2Template.__init__(self, jinja_template_file_path)
        self.threshold = threshold

    def compare_and_update(self, source_ip, source_domain, destination_ip, destination_domain, route_stats, test_time):
        """
        Compares the current route with routes from when the previous test ran.
        If no previous routes are found, the current route will be appended to the
        data_store dictionary
        :param source_ip:
        :param source_domain:
        :param destination_ip:
        :param destination_domain:
        :param route_stats:
        :param test_time:
        :return:
        """

        stats = [{"domain": hop["domain"], "as": hop["as"], "rtt": hop["rtt"]} for hop in route_stats]
        current_route = {'test_time': test_time, 'route_info': stats}
        try:
            previous = [hop["domain"] for hop in self.data_store[source_ip][destination_ip]['route_info']]
        except KeyError:
            self.data_store.setdefault(source_ip, {}).update({destination_ip: current_route})
            return

        current = [hop["domain"] for hop in route_stats]

        if self.difference_check_with_threshold(previous, current):
            print("Route Changed")
            previous_route = self.data_store[source_ip][destination_ip]
            # Update current route into data_store dictionary to prevent update by reference
            self.data_store.setdefault(source_ip, {}).update({destination_ip: current_route})

            routes = itertools.zip_longest(previous_route['route_info'],
                                           current_route['route_info'],
                                           fillvalue={"domain": "",
                                                      "as": "",
                                                      "rtt": ""})

            self.changed_routes.append({'source_domain': source_domain,
                                        'destination_domain': destination_domain,
                                        'previous_test_time': previous_route['test_time'],
                                        'current_test_time': test_time,
                                        'previous_and_current_route': routes})
        return

    def difference_check_with_threshold(self, list_a, list_b):
        """
        Performs a comparison check between two lists. It also checks for false positives when one route
        reaches all but the end node
        :param list_a:
        :param list_b:
        :return: True or False
        """
        if self.threshold > 1.0:
            raise ValueError('Threshold can not be greater than 1.0')

        if isinstance(list_a, int):
            list_a = [list_a]
        if isinstance(list_b, int):
            list_b = [list_b]

        combined_list = list(itertools.zip_longest(list_a, list_b))
        combined_list_length = len(combined_list)
        number_of_differences = len([i for i, j in combined_list if i != j])

        percentage_difference = number_of_differences / combined_list_length
        if not percentage_difference and not self.threshold:
            return False
        elif percentage_difference >= self.threshold:
            return True
        return False

    def send_email_alert(self, email_to, email_from, subject, smtp_server):
        """
        Sends an email message to recipients regarding the routes that have changed

        Email example if using html_templates/email.html.j2:
            Dear Network Admin,

            The following routes have changed:
            From owamp-ps.singaren.net.sg to nsw-brwy-ps1.aarnet.net.au

            Hop:	Previous Route:              Current Route:
            1	et-1-0-0.singaren.net.sg	et-1-0-0.singaren.net.sg0
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
        email_message = self.render_template_output(changed_routes=self.changed_routes)
        email.send_mail(email_to, email_from, subject, email_message, smtp_server)
        print("Notification email sent to %s" % ", ".join(email_to))


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
                    yield Traceroute(traceroute, web_jinja2_template_fp)
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


class Traceroute(Jinja2Template):
    def __init__(self, traceroute_test_data, jinja_template_file_path):
        """
        :param traceroute_test_data: traceroute information gathered from the main perfSONAR query
        """
        Jinja2Template.__init__(self, jinja_template_file_path)
        self.different_route_index = set()
        self.trace_route_results = json_loader_saver.retrieve_json_from_url(traceroute_test_data['api'])
        self.latest_trace_route = self.trace_route_results[-1]
        end_date = self.datetime_from_timestamps(self.latest_trace_route["ts"])
        self.information = {'source_ip': traceroute_test_data['source'],
                            'destination_ip': traceroute_test_data['destination'],
                            'source_domain': traceroute_test_data['source_domain'],
                            'destination_domain': traceroute_test_data['destination_domain'],
                            'route_stats': [],
                            'test_time': end_date}

    @staticmethod
    def __tidy_route_slice(route):
        """
        Determines whether a route is able to be tidied up in the case of trailing timeouts i.e. 'null tags:'.
        Returns the slice needed to tidy set route but does not apply said slice to route.
        :param route: traceroute route
        :return: None or slice to be performed on route
        """
        null_indices = [index for index, hop in enumerate(route) if 'null tag' in hop]
        consecutive_null_ranges = []
        if not null_indices:
            return
        if "null tag" in route[-1]:
            for k, g in itertools.groupby(enumerate(null_indices), lambda x: x[0] - x[1]):
                group = list(g)
                if len(group) > 1:
                    consecutive_null_ranges.append((group[0][1], group[-1][1]))
                else:
                    consecutive_null_ranges.append(group[0][1])
        if consecutive_null_ranges and isinstance(consecutive_null_ranges[-1], tuple):
            return slice(0, consecutive_null_ranges[-1][0] + 1)
        return

    def __generate_hop_ip_and_domain_list(self, route_test):
        """
        Returns the IP address and domain address route from the traceroute test provided by route test
        :param route_test: traceroute test
        :return:
        """
        ip_addresses = []
        domains = []
        for index, hop in enumerate(route_test["val"]):
            if "hostname" in hop:
                domains.append(hop["hostname"])
                ip_addresses.append(hop["ip"])
            elif "ip" in hop:
                domains.append(hop["ip"])
                ip_addresses.append(hop["ip"])
            else:
                null_tag = "null tag:%s_%d" % (self.information['destination_ip'], index + 1)
                domains.append(null_tag)
                ip_addresses.append(null_tag)
        slice_amount = self.__tidy_route_slice(ip_addresses)
        if slice_amount:
            domains = domains[slice_amount]
            ip_addresses = ip_addresses[slice_amount]
        return {"domains": domains, "ip_addresses": ip_addresses}

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
        Changes the epoch timestamps to its corresponding local time of the system and stores it in a list with
        the locale's date and time representation
        :param timestamps: epoch timestamp(s) e.g. 1485920150
        :return: list of converted timestamps
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
        hop_ip_and_domain_list = self.__generate_hop_ip_and_domain_list(self.latest_trace_route)
        hop_ip_list = hop_ip_and_domain_list["ip_addresses"]
        hop_domain_list = hop_ip_and_domain_list["domains"]

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
                hop_details = {key: round(float(hop_details[key]), 2)for key in hop_details}
                status = "warn" if hop_details["rtt"] > hop_details["threshold"] else "okay"
            elif len(rtt) == 1 and rtt:
                status = "unknown"
            else:
                hop_details["rtt"] = "unknown"
                status = "unknown"

            hop_details["status"] = status
            hop_details["ip"] = current_hop_ip
            hop_details["domain"] = hop_domain_list[hop_index]
            hop_details["as"] = self.__retrieve_asn(self.latest_trace_route["val"][hop_index])

            self.information['route_stats'].append(hop_details)
        return

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
            route = self.__generate_hop_ip_and_domain_list(self.trace_route_results[i])
            asn = [self.__retrieve_asn(hop) for hop in self.trace_route_results[i]["val"]]
            rtt = [round(hop['rtt'], 2) if 'rtt' in hop else "N/A" for hop in self.trace_route_results[i]["val"]]

            if (i+1 not in sorted_diff_route_index) or (previous_route != route) or (i == 0):
                data = {'index': i,
                        'timestamp': self.datetime_from_timestamps(self.trace_route_results[i]["ts"]),
                        'layer3_route': route['domains'],
                        'as_route': asn,
                        'rtt': rtt,
                        'layer3route_asn_rtt': zip(route['domains'], asn, rtt)}
                historical_routes.append(data)
            previous_route = route
        return historical_routes

    def latest_trace_output(self):
        """
        Prints out all of the current route with appropriate statistics
        :return: None
        """
        print("\nTraceroute to {ip}\n{end_date}\n".format(ip=self.information['destination_ip'],
                                                          end_date=self.information['test_time']))
        print("Hop:\tIP:\t\t\tAS:   RTT: Min: Median: Threshold: Notice:\tDomain:\n")
        for (index, hop) in enumerate(self.information['route_stats']):
            #print("{:4} {ip:24} {as:5} {rtt:6} {min:6} {median:6} {threshold:6} {status:7} {domain}".format(index + 1, **hop))
            print("{:4} {ip:24} {as:5} {rtt:6} {status:7} {domain}".format(index + 1, **hop))

    def create_traceroute_web_page(self, historical_routes):
        """
        Creates a detailed HTML traceroute results page for the current traceroute test
        :param historical_routes:
        :return:
        """
        start_date = self.datetime_from_timestamps(self.trace_route_results[0]["ts"])
        return self.render_template_output(source_ip=self.information['source_ip'],
                                           dest_ip=self.information['destination_ip'],
                                           start_date=start_date,
                                           end_date=self.information['test_time'],
                                           traceroute=self.information['route_stats'],
                                           historical_routes=historical_routes)


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
