import ipaddress
import socket
import json



class ReverseDNS:
    def __init__(self):
        self.rdns = dict()

    def query(self, ip):
        """

        :param ip:
        :return:
        """
        try:
            ipaddress.ip_address(ip)
            return self.rdns[ip]
        except ValueError:
            print("%s not a valid IP Address" % ip)
            return
        except KeyError:
            self.rdns[ip] = self._query_from_dns(ip)
            return self.rdns[ip]

    @staticmethod
    def _query_from_dns(ip):
        """

        :param ip:
        :return:
        """
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.gaierror:
            return ip
        except socket.herror:
            print("Unknown Host")
            return ip

    def load_reverse_dns_json_file(self, fp):
        """

        :param fp:
        :return:
        """
        try:
            with open(fp, "r") as rdns_file:
                self.rdns.update(json.load(fp=rdns_file))
        except FileNotFoundError:
            print("File %s not found!" % fp)

    def save_reverse_dns_json_file(self, fp):
        """

        :param fp:
        :return:
        """
        try:
            with open(fp, "w") as rdns_fp:
                json.dump(obj=self.rdns, fp=rdns_fp)
        except FileNotFoundError:
            print("Directory %s does not exist" % fp)
