import copy
from lib import jinja_renderer
from lib import email


class RouteComparison:
    def __init__(self):
        self.previous_routes = {}
        self.email_html = []

    def compare_and_update(self, source_domain, destination_domain, current_route_list):
        """
        Compares the current route with routes from when the previous test ran
        :param source_domain: Source Address
        :param destination_domain: Destination Address
        :param current_route_list: Current trace route in a list
        :return: 
        """
        try:
            if self.previous_routes[source_domain][destination_domain] != current_route_list:
                print("Route Changed")
                previous_route = self.previous_routes[source_domain][destination_domain]
                # Update current route into previous_routes dictionary
                self.previous_routes[source_domain][destination_domain] = copy.copy(current_route_list)
                # Creates email body for routes that have changed
                self.email_html.extend(["<h3>From %s to %s</h3>" % (source_domain, destination_domain)])
                self.email_html.extend(self.__create_email_template(previous_route, current_route_list))
        except KeyError:
            try:
                self.previous_routes[source_domain].update({destination_domain: current_route_list})
            except KeyError:
                self.previous_routes.update({source_domain: {destination_domain: current_route_list}})

    @staticmethod
    def __create_email_template(previous_route_list, current_route_list):
        """
        
        :param previous_route_list: 
        :param current_route_list: 
        :return: 
        """
        current_route_length = len(current_route_list)
        previous_route_length = len(previous_route_list)
        length_difference = abs(previous_route_length - current_route_length)
        max_length = previous_route_length

        if current_route_length > previous_route_length:
            max_length = current_route_length
            previous_route_list.extend(["*"] * length_difference)
        elif current_route_length < previous_route_length:
            current_route_list.extend(["*"] * length_difference)

        email_contents = ["<table>\n<tr><th>Hop:</th><th>Previous Route:</th><th>Current Route:</th></tr>"]
        for i in range(max_length):
            index, p_hop, c_hop = (i + 1, previous_route_list[i], current_route_list[i])
            email_contents.append("<tr><td>%d</td><td>%s</td><td>%s</td></tr>" % (index, p_hop, c_hop))
        email_contents.append("</table>")
        return email_contents

    def send_email_alert(self, email_to, email_from):
        subject = "Trace Route Change"
        message = self.__get_email_message()
        email.send_mail(email_to, email_from, subject, message)

    def __get_email_message(self, jinja_template_fp="html_templates/email.html.j2"):
        email_body = "".join(self.email_html)
        return jinja_renderer.render_template_output(template_fp=jinja_template_fp, route_changes=email_body)


