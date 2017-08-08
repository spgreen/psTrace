import ipaddress
import socket


class ReverseDNS:
    """
        Performs reverse DNS Lookups on valid IP addresses and stores the IP address
    and its domain name within the data store. If the IP address has no domain name,
    the IP address will be stored with itself. Assumption is if an IP address does not
    have a domain, then it will be unlikely that it will in the future.
    """
    def __init__(self):
        self.rdns_store = dict()

    def query(self, *ip_addresses):
        """
            Performs a reverse DNS lookup on IP addresses by first looking through the
        rdns_store dictionary. If nothing is found within the said dictionary it will
        then query from the DNS server.
        :param ip_addresses: IP Address to be queried
        :return: list; domain names of said IP addresses
        """
        ip_store = []
        for ip_address in ip_addresses:
            try:
                ipaddress.ip_address(ip_address)
                ip_store.append(self.rdns_store[ip_address])
            except ValueError:
                print("Error: %s not a valid IP Address" % ip_address)
                ip_store.append(ip_address)
            except KeyError:
                self.rdns_store[ip_address] = self.__query_from_dns(ip_address)
                ip_store.append(self.rdns_store[ip_address])
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
