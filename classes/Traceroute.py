import statistics
import time

from lib import json_loader_saver
from lib import jinja_renderer


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
        upper_index = int(number_list_size/2) + 1
        lower_index = upper_index - 1
    else:
        upper_index = int(number_list_size/2)
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


def datetime_from_timestamps(*timestamps):
    """
    
    :param timestamps: 
    :return: 
    """
    ts_store = [time.strftime("%c", time.localtime(int(ts))) for ts in timestamps]
    if len(ts_store) == 1:
        return ts_store[0]
    return ts_store


class Traceroute:
    def __init__(self, test_info):
        """
        
        :param test_info: traceroute information gathered from the main perfSONAR query
        """
        self.route_stats = []
        self.different_route_index = set()
        self.source_domain = ""
        self.destination_domain = ""
        self.hop_ip_list = ""

        self.source_ip = test_info['source']
        self.destination_ip = test_info['destination']
        self.trace_route_results = json_loader_saver.retrieve_json_from_url(test_info['api'])
        self.latest_trace_route = self.trace_route_results[len(self.trace_route_results) - 1]
        self.start_date, self.end_date = datetime_from_timestamps(self.trace_route_results[0]["ts"], self.latest_trace_route["ts"])

    def __generate_hop_lists(self, route_test):
        """
        Retrieves the traceroute from traceroute test index from self.trace_route_results[index]
        :param route_test: raw trace route test from self.trace_route_results[index]
        :return: trace route for traceroute_test
        """
        return [hop["ip"] if "ip" in hop else "null tag:%s:%d" % (self.destination_domain, index + 1)
                for (index, hop) in enumerate(route_test["val"])]

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

    def traceroute_analysis(self):
        """
        Performs latest_route_analysis on the most recent traceroute against previous traceroute test
        :return: route statistics for the most recent traceroute
        """
        # Retrieves latest route from self.trace_route_results
        self.hop_ip_list = self.__generate_hop_lists(self.latest_trace_route)

        for (hop_index, current_hop_ip) in enumerate(self.hop_ip_list):
            # Goes through every test comparing the IP occurring at the same hop_index of the latest trace route
            rtt = []
            if "null tag:" not in current_hop_ip:
                rtt = self.retrieve_all_rtts_for_hop(hop_index=hop_index,  hop_ip=current_hop_ip)

            hop_details = five_number_summary(rtt)
            # Save last value of the rtt as it is from the latest trace route; save empty value if rtt does not exist
            hop_details["rtt"] = rtt[-1] if rtt else ""

            if len(rtt) > 1 and rtt:
                # rounds all hop_details to 2 d.p.s
                hop_details = {key: round(hop_details[key], 2)for key in hop_details}
                status = "warn" if hop_details["rtt"] > hop_details["threshold"] else "okay"
            else:
                hop_details["rtt"] = "unknown"
                status = "unknown"

            hop_details["status"] = status
            hop_details["ip"] = current_hop_ip
            self.route_stats.append(hop_details)
        return self.route_stats

    def historical_diff_routes(self):
        """
        Acquires the trace routes that are different from the most recent trace route test and stores them within a list
        :return: 
        """
        previous_route = ""
        historical_routes = []
        # Ends if no different routes were found at retrieve_all_rtts_for_hop during traceroute_analysis call
        if not self.different_route_index:
            return
        # Reverse sort the different route index list as higher indexes indicate more recent dates
        sorted_diff_route_index = sorted(list(self.different_route_index), reverse=True)
        # Retrieves all of the different routes that occurred during the data period and stores the routes within the
        # historical_routes list
        for i in sorted_diff_route_index:
            route = self.__generate_hop_lists(self.trace_route_results[i])
            if (i+1 not in sorted_diff_route_index) or (previous_route != route) or (i == 0):
                data = {'index': i, 'ts': datetime_from_timestamps(self.trace_route_results[i]["ts"]), 'route': route}
                historical_routes.append(data)
            previous_route = route
        return historical_routes

    def latest_trace_output(self):
        """
        Prints out all of the current route with appropriate statistics
        :return: 
        """
        print("\nTraceroute to {ip}\n{end_date}\n".format(ip=self.destination_ip, end_date=self.end_date))
        print("Hop:\tIP:\t\t\tRTT: Min: Median: Threshold: Notice:\tDomain:\n")
        for (index, hop) in enumerate(self.route_stats):
            print("{:4} {ip:24} {rtt:6} {min:6} {median:6} {threshold:6} {status:7} {domain}".format(index + 1, **hop))

    @staticmethod
    def __create_historical_route_html(historical_routes):
        html_historical = ["<h2>Historical Routes</h2>"]
        for h_route in historical_routes:
            html_historical.append("<p>{ts}</p>\n"
                                   "<table border='1'>\n"
                                   "<tr><td>Hop:</td><td>IP:</td></tr>\n".format(ts=h_route["ts"]))
            for (index, hop) in enumerate(h_route["route"]):
                html_historical.append("<tr><td>{index}</td><td>{ip}</td></tr>\n".format(index=index + 1, ip=hop))
            html_historical.append("</table>\n")
        return "".join(html_historical)

    def create_traceroute_web_page(self, historical_routes, jinja_template_fp):
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

            html_hop = ("<tr><td>{index}</td><td>{domain}</td><td>{ip}</td><td>{rtt}</td><td>{min}</td>"
                        "<td>{median}</td><td>{threshold}</td><td>{web_status}</td></tr>\n")
            html_route.append(html_hop.format(index=index + 1, web_status=html_status, **hop_stats))

        html_route = "".join(html_route)

        return jinja_renderer.render_template_output(template_fp= jinja_template_fp,
                                                     source_ip=self.source_ip,
                                                     dest_ip=self.destination_ip,
                                                     start_date=self.start_date,
                                                     end_date=self.end_date,
                                                     traceroute=html_route,
                                                     historical=html_historical)
