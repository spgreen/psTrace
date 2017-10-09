import copy
import itertools

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
    number_of_differences = len([i for i, j in combined_list if i == j])

    if number_of_differences/combined_list_length < threshold:
        return True
    return False


class RouteComparison:
    """
    Used for comparing two traceroute tests. If current route is different
     to the previous test, the new route will be saved and a HTML body
     comparing the two routes will be generated to be sent off as an HTML email.
    The class calls on the jinja_renderer function to load Jinja2 templates
     used for the email message and the email function to send said generated
     HTML email message.
    """
    def __init__(self, threshold):
        self.previous_routes = {}
        self.email_contents = []
        self.threshold = threshold

    def compare_and_update(self, src_domain, dest_domain, current_route):
        """
        Compares the current route with routes from when the previous test ran.
        If no previous routes are found, the current route will be appended to the
        previous_routes dictionary
        :param src_domain: Source domain name
        :type src_domain: str
        :param dest_domain: Destination domain name
        :type dest_domain: str
        :param current_route: Current trace route list
        :type current_route: list
        :return: None
        """
        try:
            if comparison_check(self.previous_routes[src_domain][dest_domain], current_route, self.threshold):
                print("Route Changed")
                previous_route = self.previous_routes[src_domain][dest_domain]
                # Update current route into previous_routes dictionary to prevent update by reference
                self.previous_routes[src_domain][dest_domain] = copy.copy(current_route)

                # Creates email body for routes that have changed
                self.email_contents.extend(["<h3>From %s to %s</h3>" % (src_domain, dest_domain)])
                self.email_contents.extend(self.__create_email_message(previous_route, current_route))
        except KeyError:
            try:
                self.previous_routes[src_domain].update({dest_domain: current_route})
            except KeyError:
                self.previous_routes.update({src_domain: {dest_domain: current_route}})

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
        combined_route = itertools.zip_longest(previous_route, current_route, fillvalue="*")
        html = ["<table>\n<tr><th>Hop:</th><th>Previous Route:</th><th>Current Route:</th></tr>"]
        for index, route in enumerate(combined_route):
            html.append("\n<tr><td>%d</td><td>%s</td><td>%s</td></tr>" % (index + 1, route[0], route[1]))
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
