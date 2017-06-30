from lib import date_retrieval, AcquireTracerouteTestAPI
from lib import reverse_dns
from lib.five_number_summary import five_number_summary


class Traceroute:
    hop_ip_list = [] # trace route ip path
    previous_hop_list = []

    def __init__(self, test_info):
        """
        
        :param test_info: traceroute information gathered from the main perfSONAR query
        """
        self.route_stats = []
        self.api_key = test_info['api']
        self.source_ip = test_info['source']
        self.destination_ip = test_info['destination']
        self.different_route_index = set()

        self.test_results = AcquireTracerouteTestAPI.retrieve_json_from_url(self.api_key)
        max_tests = len(self.test_results)
        self.latest_route = self.test_results[max_tests - 1]
        self.start_date = date_retrieval.get_datetime_from_timestamp(self.test_results[0]["ts"])
        self.end_date = date_retrieval.get_datetime_from_timestamp(self.latest_route["ts"])

    def _generate_hop_lists(self, traceroute_test):
        """
        Retrieves the traceroute from traceroute test index from self.test_results[index]
        :param traceroute_test: raw trace route test from self.test_results[index]
        :return: trace route for traceroute_test
        """
        return [(hop["ip"] if "ip" in hop else "null tag:{}".format(self.destination_ip))
                for (index, hop) in enumerate(traceroute_test["val"])]

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

        for (test_index, traceroute_test) in enumerate(self.test_results):
            try:
                if traceroute_test["val"][hop_index]["ip"] == hop_ip:
                    rtt_append(traceroute_test["val"][hop_index]["rtt"])
                else:
                    self.different_route_index.add(test_index)
            except KeyError:
                self.different_route_index.add(test_index)
                continue
            except IndexError:
                self.different_route_index.add(test_index)
                continue
        return rtt

    def traceroute_analysis(self, rdns):
        """
        Performs latest_route_analysis on the most recent traceroute against previous traceroute test
        :return: route statistics for the most recent traceroute
        """
        # Retrieves latest route from self.test_results
        hop_ip_list = self._generate_hop_lists(self.latest_route)

        for (hop_index, current_hop_ip) in enumerate(hop_ip_list):
            # Goes through every test comparing the IP occurring at the same hop_index of the latest trace route
            rtt = []
            if current_hop_ip != "null tag:{}".format(self.destination_ip):
                rtt = self.retrieve_all_rtts_for_hop(hop_index=hop_index,  hop_ip=current_hop_ip)

            hop_details = five_number_summary(rtt)
            # Retrieves round trip time for the current hop. If round trip time does not exist,
            # an asterisk will be used in place
            hop_details["rtt"] = self.latest_route["val"][hop_index]["rtt"] if "rtt" in self.latest_route["val"][hop_index] else "*"

            if len(rtt) > 1 and "null" not in rtt:
                # rounds all hop_details to 2 d.p.s
                hop_details = {key: round(hop_details[key], 2)for key in hop_details}
                status = "warn" if hop_details["rtt"] > hop_details["threshold"] else "okay"
            else:
                status = "unknown"

            hop_details["status"] = status
            hop_details["ip"] = current_hop_ip
            hop_details["domain"] = reverse_dns.query(current_hop_ip, rdns)

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
            route = self._generate_hop_lists(self.test_results[i])
            if (i+1 not in sorted_diff_route_index) or (previous_route != route) or (i == 0):
                time = date_retrieval.get_datetime_from_timestamp(self.test_results[i]["ts"])
                data = dict(index=i, ts=time, route=route )
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
            print("{:4} {ip:24} {rtt:6} {min:6} {median:6} {threshold:6} {status:7} {domain}".format(index + 1,**hop))
