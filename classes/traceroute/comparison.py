import itertools

from classes.base import DataStore, Jinja2Template
from lib import email


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

    @staticmethod
    def compare_three_objects(first, second, third):
        """
        Performs an ordered comparison on three objects and returns a message depending
        on the results from the logic table below.

        Logic Table:
        |A|B||C|
        |0|0||0| = No Change
        |0|0||1| = Warning
        |0|1||0| = Flapping
        |0|1||1| = Change
        |1|0||0| = Change
        |1|0||1| = Flapping
        |1|1||0| = Warning
        |1|1||1| = No Change

        :param first:
        :param second:
        :param third:
        :return:
        """
        if first != second == third:
            return 'CHANGE'
        elif first != second != third:
            return 'FLAP'
        elif first == second != third:
            return 'WARN'
        return

    def _retrieve_historical_route_data(self, source_ip, destination_ip, current_route):
        """
        Retrieves the last two historical tests from the historical data store (self.data_store).
        If neither the first nor second test exist, the function will update the data store with
        the current route.
        :param source_ip: Source IP address of the current traceroute test
        :param destination_ip: Destination IP address of the current traceroute test
        :param current_route: Route statistics of the current the traceroute test
        :return: None or first_historical_route, second_historical_route
        """
        try:
            first_historical_route = self.data_store[source_ip][destination_ip]['first_result']
        except KeyError:
            self.data_store.setdefault(source_ip, {}).update({destination_ip: {'first_result': current_route,
                                                                               'flapping': 0}})
            return
        try:
            second_historical_route = self.data_store[source_ip][destination_ip]['second_result']
        except KeyError:
            self.data_store[source_ip][destination_ip].update({'second_result': current_route})
            return
        return first_historical_route, second_historical_route

    @staticmethod
    def _retrieve_ip_route_from_route_data(*args):
        """
        Retrieves the IP address route from multiple sets of route data within *args
        and returns it all IP routes within a nested list.
        :param args: traceroute data in Traceroute.information form
        :return: Nested list of each IP route found in *args
        """
        return [[hop.get('ip')for hop in route['route_stats']] for route in args]

    def check_changes(self, traceroute):
        """
        Compares the current route with the last two significant traceroute results.
        It updates the historical traceroute test data store and preps the variables
        needed if an email notification for a route flap/change occurs.
        If no previous routes are found, the current route will be added to the
        data_store dictionary
        :param traceroute: Traceroute data in the form of Traceroute.information
        :return: None
        """
        source_ip, destination_ip = traceroute['source_ip'], traceroute['destination_ip']
        current_route = {'test_time': traceroute['test_time'],
                         'route_stats': traceroute['route_stats']}

        historical_routes = self._retrieve_historical_route_data(source_ip, destination_ip, current_route)
        if not historical_routes:
            return
        first_route, second_route = historical_routes[0], historical_routes[1]

        flap_tag = self.data_store[source_ip][destination_ip].get('flapping')
        ip_routes = self._retrieve_ip_route_from_route_data(first_route, second_route, current_route)
        status = self.compare_three_objects(ip_routes[0], ip_routes[1], ip_routes[2])
        if status is None:
            return

        print(status)
        previous_route = first_route
        self.data_store[source_ip][destination_ip].update({'first_result': second_route,
                                                           'second_result': current_route})

        if 'FLAP' in status:
            if flap_tag:
                return
            self.data_store[source_ip][destination_ip]['flapping'] = 1
            previous_route = second_route
        elif 'WARN' in status:
            return
        elif 'CHANGE' in status:
            self.data_store[source_ip][destination_ip]['flapping'] = 0

        routes = itertools.zip_longest(previous_route['route_stats'], traceroute['route_stats'])
        self.changed_routes.append({'source_domain': traceroute['source_domain'],
                                    'destination_domain': traceroute['destination_domain'],
                                    'previous_test_time': previous_route['test_time'],
                                    'current_test_time': traceroute['test_time'],
                                    'previous_and_current_route': routes,
                                    'status': status})
        return

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
