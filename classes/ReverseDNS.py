import ipaddress
import socket


class ReverseDNS:
    def __init__(self):
        self.rdns_store = dict()

    def query(self, *ip_addresses):
        """

        :param ip_addresses:
        :return:
        """
        ip_store = []
        for ip in ip_addresses:
            try:
                ipaddress.ip_address(ip)
                ip_store.append(self.rdns_store[ip])
            except ValueError:
                print("%s not a valid IP Address" % ip)
                ip_store.append(ip)
            except KeyError:
                self.rdns_store[ip] = self.__query_from_dns(ip)
                ip_store.append(self.rdns_store[ip])
        if len(ip_store) == 1:
            return ip_store[0]
        return ip_store

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
