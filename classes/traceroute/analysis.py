#!/usr/bin/python3
"""Provides the TracerouteAnalysis class for traceroute analysis.

Acquires, cleans and analyses PerfSONAR traceroute test data from a PerfSONAR Measurement Archive (MA).
It also provides an option to output the results via the console or as a web page.
"""

import statistics
import time

from classes.base import Jinja2Template
from lib import json_loader_saver

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


class TracerouteAnalysis(Jinja2Template):
    def __init__(self, traceroute_test_data, jinja_template_file_path):
        """
        Performs initial retrieval of traceroute data and variables needed for analysis.
        :param traceroute_test_data: traceroute information gathered from the main perfSONAR query
        """
        Jinja2Template.__init__(self, jinja_template_file_path)
        self.different_route_index = set()
        self.trace_route_results = json_loader_saver.retrieve_json_from_url(traceroute_test_data['api'])
        latest_trace_route = self.trace_route_results[-1]
        self.route_info = self.route_cleaner(latest_trace_route['val'])
        self.information = {'source_ip': traceroute_test_data['source'],
                            'destination_ip': traceroute_test_data['destination'],
                            'source_domain': traceroute_test_data['source_domain'],
                            'destination_domain': traceroute_test_data['destination_domain'],
                            'route_stats': self.route_info,
                            'test_time': self.datetime_from_timestamps(latest_trace_route['ts'])}

    @staticmethod
    def _tidy_route_slice(route):
        """
        Determines whether a route is able to be tidied up in the case of trailing timeouts i.e. '*'.
        Returns the slice needed to tidy the traceroute.
        :param route: traceroute route
        :return: None or slice to be performed on route
        """

        if '*' not in str(route[-1]['rtt']):
            return
        route_reversed = reversed(route)
        count = -1
        for hop in route_reversed:
            if '*' not in hop.values():
                break
            count += 1
        if count > 0:
            return slice(-count)
        return

    def route_cleaner(self, route):
        """

        :param route:
        :return:
        """
        for hop in route:
            hop['hostname'] = hop.setdefault('hostname', hop.get('ip', '*'))
            if hop.get('hostname') == 'gateway':
                hop['hostname'] = hop.get('ip', '*')
            hop['ip'] = hop.setdefault('ip', '*')
            try:
                hop['as'] = hop.get('as', {}).get('number', '*')
            except AttributeError:
                hop['as'] = hop.get('as', '*')
            try:
                hop['rtt'] = round(hop['rtt'], 2)
            except (TypeError, KeyError):
                hop['rtt'] = hop.get('rtt', '*')
        slice_amount = self._tidy_route_slice(route)
        if slice_amount:
            route = route[slice_amount]
        return route

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
        try:
            number_list_size = len(number_list)
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
        if "*" in hop_ip:
            return
        rtt = []
        rtt_append = rtt.append
        different_route_add = self.different_route_index.add
        for (test_index, traceroute_test) in enumerate(self.trace_route_results):
            try:
                if traceroute_test["val"][hop_index]["ip"] == hop_ip:
                    rtt_append(float(traceroute_test["val"][hop_index]["rtt"]))
                else:
                    different_route_add(test_index)
            except (KeyError, IndexError, ValueError):
                different_route_add(test_index)
                continue
        return rtt

    def perform_traceroute_analysis(self):
        """
        Performs latest_route_analysis on the most recent traceroute against previous traceroute test
        Retrieves statistical information for the specified hop and updates route_info with said statistics.
        :return: route statistics for the most recent traceroute
        """
        for (hop_index, hop_info) in enumerate(self.route_info):
            rtt = self.retrieve_all_rtts_for_hop(hop_index=hop_index, hop_ip=hop_info.get('ip'))

            hop_details = self.five_number_summary(rtt)
            status = "unknown"

            if rtt:
                # Save last value of the rtt as it is from the latest trace route; save empty value if rtt does not exist
                most_recent_rtt = round(rtt[-1], 2)
                # rounds all hop_detail items to 2 d.p.s
                hop_details = {key: round(float(value), 2) if value else most_recent_rtt
                               for key, value in hop_details.items()}
                status = "warn" if most_recent_rtt > hop_details["threshold"] else "okay"
            hop_details['hop_number'] = hop_index + 1
            hop_details["status"] = status
            hop_info.update(hop_details)
        return self.route_info

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
            changed_traceroute = self.trace_route_results[i]
            route = [hop.get('ip', '*') for hop in changed_traceroute['val']]

            if previous_route != route:
                historical_routes.append({'date_time': self.datetime_from_timestamps(changed_traceroute['ts']),
                                          'route_info': self.route_cleaner(changed_traceroute['val'])})
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
            print("{:4} {ip:24} {as:5} {rtt:6} {status:7} {hostname}".format(index + 1, **hop))

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

    def __str__(self):
        return "Traceroute({source}, {destination})".format(source=self.information['source_domain'],
                                                            destination=self.information['destination_domain'])
