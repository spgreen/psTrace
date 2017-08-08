import copy
from lib import jinja_renderer
from lib import email


class RouteComparison:
    """
    Used for comparing two traceroute tests. If current route is different
     to the previous test, the new route will be saved and a HTML body
     comparing the two routes will be generated to be sent off as an HTML email.
    The class calls on the jinja_renderer function to load Jinja2 templates
     used for the email message and the email function to send said generated
     HTML email message.
    """
    def __init__(self):
        self.previous_routes = {}
        self.email_contents = []

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
            if self.previous_routes[src_domain][dest_domain] != current_route:
                print("Route Changed")
                previous_route = self.previous_routes[src_domain][dest_domain]
                # Update current route into previous_routes dictionary
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
        current_route_length = len(current_route)
        previous_route_length = len(previous_route)
        length_difference = abs(previous_route_length - current_route_length)
        max_length = previous_route_length

        # Adds "*" padding to the shortest route to ensure the current and previous route
        # are of equal length
        if current_route_length > previous_route_length:
            max_length = current_route_length
            previous_route.extend(["*"] * length_difference)
        elif current_route_length < previous_route_length:
            current_route.extend(["*"] * length_difference)

        html = ["<table>\n<tr><th>Hop:</th><th>Previous Route:</th><th>Current Route:</th></tr>"]
        for i in range(max_length):
            index, p_hop, c_hop = (i + 1, previous_route[i], current_route[i])
            html.append("<tr><td>%d</td><td>%s</td><td>%s</td></tr>\n" % (index, p_hop, c_hop))
        html.append("</table>")
        return html

    def send_email_alert(self, email_to, email_from, jinja_template_fp):
        """
        Sends an email message to recipients regarding the routes that have changed

        Email example if using html_templates/matrix.html.j2:
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

        :param email_to: E-mail addresses of the receivers
        :type email_to: list
        :param email_from: E-mail address of the sender
        :type email_from: str
        :param jinja_template_fp: File path of the template file
        :type jinja_template_fp: str
        :return: None
        """
        subject = "Trace Route Change"
        email_body = "".join(self.email_contents)
        message = jinja_renderer.render_template_output(template_fp=jinja_template_fp,
                                                        route_changes=email_body)
        email.send_mail(email_to, email_from, subject, message)
