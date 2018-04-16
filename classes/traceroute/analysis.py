import itertools
import statistics
import time

from classes.base import Jinja2Template
from lib import json_loader_saver


class TracerouteAnalysis(Jinja2Template):
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
