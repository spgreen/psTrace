import ipaddress
import socket


class ReverseDNS:
    def __init__(self):
        self.rdns_store = dict()

    def query(self, ip):
        """

        :param ip:
        :return:
        """
        try:
            ipaddress.ip_address(ip)
            return self.rdns_store[ip]
        except ValueError:
            print("%s not a valid IP Address" % ip)
            return ip
        except KeyError:
            self.rdns_store[ip] = self.__query_from_dns(ip)
            return self.rdns_store[ip]

    @staticmethod
    def __query_from_dns(ip):
        """

        :param ip:
        :return:
        """
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.gaierror:
            return ip
        except socket.herror:
            print("Unknown Host: %s" % ip)
            return ip
