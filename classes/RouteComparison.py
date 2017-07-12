from lib import jinja_renderer
from lib import email


class RouteComparison:
    def __init__(self):
        self.previous_routes = {}
        self.email_html = []

    def compare_and_update(self, source_ip, dest_ip, current_route_list):
        """
        Compares the current route with routes from when the previous test ran
        :param source_ip: Source IP Address
        :param dest_ip: Destination IP Address
        :param current_route_list: Current trace route in a list
        :return: 
        """
        try:
            if self.previous_routes[source_ip][dest_ip] != current_route_list:
                print("Route Changed")
                previous_route = self.previous_routes[source_ip][dest_ip]
                self.email_html.extend(["<h3>From %s to %s</h3>" % (source_ip, dest_ip)])
                self.email_html.extend(self.__create_email_template(previous_route, current_route_list))
                self.previous_routes[source_ip][dest_ip] = current_route_list
        except KeyError:
            try:
                self.previous_routes[source_ip].update({dest_ip: current_route_list})
            except KeyError:
                self.previous_routes.update({source_ip: {dest_ip: current_route_list}})

    @staticmethod
    def __create_email_template(previous_route_list, current_route_list):
        """
        
        :param previous_route_list: 
        :param current_route_list: 
        :return: 
        """
        current_route_length = len(current_route_list)
        previous_route_length = len(previous_route_list)
        max_length = previous_route_length
        if current_route_length > previous_route_length:
            max_length = current_route_length
            previous_route_list += ["*" for i in range(max_length - previous_route_length)]
        elif current_route_length < previous_route_length:
            current_route_list += ["*" for i in range(max_length-current_route_length)]

        email_contents = ["<table>\n<th><td>Hop:</td><td>Previous Route:</td><td>Current Route:</td></th>"]
        for i in range(max_length):
            index, p_hop, c_hop = (i + 1, previous_route_list[i], current_route_list[i])
            email_contents.append("<tr><td>%d</td><td>%s</td><td>%s</td></tr>" % (index, p_hop, c_hop))
        email_contents.append("</table>")
        return email_contents

    def send_email_alert(self, email_to, email_from):
        subject = "Trace Route Change"
        email.send_mail(email_to, email_from, subject, self.__get_email_message())

    def __get_email_message(self, jinja_template_fp="html_templates/email.html.j2"):
        email_body = "".join(self.email_html)
        return jinja_renderer.render_template_output(template_fp=jinja_template_fp, route_changes=email_body)


