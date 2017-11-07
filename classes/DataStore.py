import copy
import ipaddress
import itertools
import json
import socket

from conf.email_configuration import EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, EMAIL_SERVER
from lib import email
from lib import jinja_renderer


def comparison_check(list_a, list_b, threshold):
    """
    
    :param list_a: 
    :param list_b: 
    :param threshold: 
    :return: 
    """
    if not (list_a or list_b):
        raise ValueError
    if isinstance(list_a, int) or isinstance(list_b, int):
        raise TypeError
    if threshold > 1.0:
        raise ValueError

    combined_list = list(itertools.zip_longest(list_a, list_b))
    combined_list_length = len(combined_list)
    number_of_differences = len([i for i, j in combined_list if i != j])

    if number_of_differences/combined_list_length > threshold:
        return True


class DictionaryDataStore:

    def __init__(self):
        self.dictionary_store = {}

    def update_dictionary_from_json_file(self, file_path):
        """
        Updates dictionary with from a JSON file
        :param file_path: file path of the JSON file to load
        :return: 
        """
        try:
            with open(file_path, "r") as file:
                self.dictionary_store.update(json.load(fp=file))
        except FileNotFoundError:
            print("File %s not found!" % file_path)
        except ValueError:
            print("Error: Unable to update due to different dictionary_contents length")


class RouteComparison(DictionaryDataStore):
    """
    Used for comparing two traceroute tests. If current route is different
     to the previous test, the new route will be saved and a HTML body
     comparing the two routes will be generated to be sent off as an HTML email.
    The class calls on the jinja_renderer function to load Jinja2 templates
     used for the email message and the email function to send said generated
     HTML email message.
    """
    def __init__(self, threshold):
        DictionaryDataStore.__init__(self)
        self.email_contents = []
        self.threshold = threshold

    def compare_and_update(self, src_domain, dest_domain, route_stats):
        """
        Compares the current route with routes from when the previous test ran.
        If no previous routes are found, the current route will be appended to the
        dictionary_store dictionary
        :param src_domain: Source domain name
        :type src_domain: str
        :param dest_domain: Destination domain name
        :type dest_domain: str
        :param route_stats: Current trace route list
        :type route_stats: list
        :return: None
        """
        statistics = [{"domain": hop["domain"], "as": hop["as"], "rtt": hop["rtt"]} for hop in route_stats]
        try:
            previous = (hop["domain"] for hop in self.dictionary_store[src_domain][dest_domain])
            current = (hop["domain"] for hop in route_stats)

            if comparison_check(previous, current, self.threshold):
                print("Route Changed")
                previous_route = self.dictionary_store[src_domain][dest_domain]
                # Update current route into dictionary_store dictionary to prevent update by reference
                self.dictionary_store[src_domain][dest_domain] = copy.copy(statistics)

                # Creates email body for routes that have changed
                self.email_contents.extend(["<h3>From %s to %s</h3>" % (src_domain, dest_domain)])
                self.email_contents.extend(self.__create_email_message(previous_route, statistics))
        except KeyError:
            try:
                self.dictionary_store[src_domain].update({dest_domain: statistics})
            except KeyError:
                self.dictionary_store.update({src_domain: {dest_domain: statistics}})

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
                                                          "rtt": "*"}
                                               )
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

    def send_email_alert(self, jinja_template_fp):
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
            
        :param jinja_template_fp: File path of the template file
        :type jinja_template_fp: str
        :return: None
        """
        email_body = "".join(self.email_contents)
        email_message = jinja_renderer.render_template_output(template_fp=jinja_template_fp,
                                                              route_changes=email_body)
        email.send_mail(EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, email_message, EMAIL_SERVER)
        print("Notification email sent to %s" % ", ".join(EMAIL_TO))


class ReverseDNS(DictionaryDataStore):
    """
    Performs reverse DNS Lookups on valid IP addresses and stores the IP address
    and its domain name within the data store. If the IP address has no domain name,
    the IP address will be stored with itself. Assumption is if an IP address does not
    have a domain, then it will be unlikely that it will in the future.
    """
    def __init__(self):
        DictionaryDataStore.__init__(self)

    def query(self, *ip_addresses):
        """
        Performs a reverse DNS lookup on IP addresses by first looking through the
        dictionary_store dictionary. If nothing is found within the said dictionary it will perform 
        a query the DNS server.
        :param ip_addresses: IP Address to be queried
        :return: list; domain names of said IP addresses
        """
        ip_store = []
        for ip_address in ip_addresses:
            try:
                ipaddress.ip_address(ip_address)
                ip_store.append(self.dictionary_store[ip_address])
            except ValueError:
                #print("Error: %s not a valid IP Address" % ip_address)
                ip_store.append(ip_address)
            except KeyError:
                self.dictionary_store[ip_address] = self.__query_from_dns(ip_address)
                ip_store.append(self.dictionary_store[ip_address])
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
