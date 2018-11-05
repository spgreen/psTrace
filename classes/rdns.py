#!/usr/bin/python3
"""Provides the ReverseDNS class for reverse DNS lookups

Performs IP address to domain name lookups from the systems DNS server
and stores the results in JSON format to allow for dictionary lookups.
If previous results are loaded in, it will perform the lookup
on the dictionary corresponding to the JSON file first
before querying the DNS server.
"""

import ipaddress
import socket
from classes.base import DataStore

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


class ReverseDNS(DataStore):
    """
    Performs reverse DNS Lookups on valid IP addresses and stores the IP address
    and its domain name within the data store. If the IP address has no domain name,
    the IP address will be stored with itself. Assumption is if an IP address does not
    have a domain, then it will be unlikely that it will in the future.
    """
    def __init__(self):
        DataStore.__init__(self)

    def query(self, *ip_addresses):
        """
        Performs a reverse DNS lookup on IP addresses by first looking through the
        data_store dictionary. If nothing is found within the said dictionary it will perform
        a query the DNS server.
        :param ip_addresses: IP Address to be queried
        :return: list; domain names of said IP addresses
        """
        ip_store = []
        for ip_address in ip_addresses:
            try:
                ipaddress.ip_address(ip_address)
                ip_store.append(self.data_store[ip_address])
            except ValueError:
                #print("Error: %s not a valid IP Address" % ip_address)
                ip_store.append(ip_address)
            except KeyError:
                self.data_store[ip_address] = self.__query_from_dns(ip_address)
                ip_store.append(self.data_store[ip_address])
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
