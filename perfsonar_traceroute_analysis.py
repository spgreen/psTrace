#!/usr/bin/python3
"""
TODO: Add Description
"""

import argparse
import datetime
import os.path
import ipaddress
import configparser
import urllib.parse
from urllib.error import HTTPError
from classes.rdns import ReverseDNS
from classes.pstrace import PsTrace
from classes.base import Jinja2Template
from lib import json_loader_saver

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(BASE_DIR, 'config.ini'))

TESTING_PERIOD = int(CONFIG['PERFSONAR']['MAX_TIME_BETWEEN_TESTS'])
THRESHOLD = float(CONFIG['ROUTE_COMPARISON']['THRESHOLD'])
EMAIL_ALERTS = int(CONFIG['EMAIL']['ALERTS'])
EMAIL_TO = CONFIG['EMAIL']['TO'].replace(' ', '').split(',')
EMAIL_FROM = CONFIG['EMAIL']['FROM']
EMAIL_SUBJECT = CONFIG['EMAIL']['SUBJECT']
SMTP_SERVER = CONFIG['EMAIL']['SMTP_SERVER']

# Directories
HTML_DIR = os.path.join(BASE_DIR, "html")
JSON_DIR = os.path.join(BASE_DIR, "json")
TEMPLATE_DIR = os.path.join(BASE_DIR, "html_templates")

# HTML Folder
FORCE_GRAPH_DATA_FP = os.path.join(HTML_DIR, "traceroute_force_graph.json")
DASHBOARD_WEB_PAGE_FP = os.path.join(HTML_DIR, "index.html")

# JSON Folder
REVERSE_DNS_FP = os.path.join(JSON_DIR, "rdns.json")
PREVIOUS_ROUTE_FP = os.path.join(JSON_DIR, "previous_routes.json")

# Jinja2 Templates
J2_EMAIL_TEMPLATE_FP = os.path.join(TEMPLATE_DIR, "email.html.j2")
J2_TRACEROUTE_WEB_PAGE_FP = os.path.join(TEMPLATE_DIR, "traceroute.html.j2")
J2_MATRIX_WEB_PAGE_FP = os.path.join(TEMPLATE_DIR, "matrix.html.j2")


def acquire_traceroute_tests(ps_node_urls, rdns_query, test_time_range=2400):
    """
    Acquires all recent traceroute results from a PerfSONAR Measurement Archive
    :param ps_node_urls: Base URL of PerfSONAR MA
    :param test_time_range: time range in seconds of tests to retrieve
    :param rdns_query: Reverse DNS function
    :return: 
    """
    if not isinstance(test_time_range, int):
        raise ValueError

    traceroute_tests = []
    for url in ps_node_urls:
        ps_url = "https://%s/esmond/perfsonar/archive/?event-type=packet-trace&time-range=%d" % (url, TESTING_PERIOD)
        try:
            traceroute_tests.extend(json_loader_saver.retrieve_json_from_url(ps_url))
        except HTTPError as error:
            print("%s - Unable to retrieve perfSONAR traceroute data from %s. Continuing..." % (error, url))

    for singular_test in traceroute_tests:
        url = urllib.parse.urlsplit(singular_test['url'], scheme="https")
        api_key = "https://{}{}packet-trace/base?time-range={}".format(url.netloc, url.path, test_time_range)

        yield {'api': api_key,
               'source': singular_test['source'],
               'destination': singular_test["destination"],
               'source_domain': rdns_query(singular_test['source']),
               'destination_domain': rdns_query(singular_test["destination"])}


def create_matrix_html(source_list, destination_list, matrix, rdns_query):
    """
    Creates the html code for the matrix table by using the source and destination entries
    to retrieve each item from the matrix dictionary.
    :param source_list: Traceroute test source IPs
    :param destination_list: Traceroute test destination IPs
    :param matrix: Dictionary containing basic traceroute test information (i.e. html file path and RTT)
    :param rdns_query: function that performs a Reverse DNS query
    :return:
    """
    def ipv6_label(ip, domain):
        """
        Returns a domain name with IPv6 tagged to the end if the IP address is IPv6 otherwise it
        returns just the domain name.
        :param ip: IP Address
        :param domain: Domain name address
        :return: str
        """
        ip_version = ipaddress.ip_address(ip).version
        return " ".join([domain, '(IPv6)']) if ip_version is 6 else domain

    html = ['<tr><td>S/D</td>']
    for destination in destination_list:
        label = ipv6_label(destination, rdns_query(destination))
        html.append('<td><div><span>{}</span></div></td>'.format(label))
    html.append('</tr>')
    for source in source_list:
        label = ipv6_label(source, rdns_query(source))
        html.append('<tr><td>{}</td>'.format(label))
        for destination in destination_list:
            try:
                html.append('<td><a href="{fp_html}">{rtt}</a></td>'.format(**matrix[source][destination]))
            except KeyError:
                html.append('<td></td>')
        html.append('</tr>')
    return ''.join(html)


def main(perfsonar_ma_url, time_period):
    """
    TODO: Add Description
    :param perfsonar_ma_url:
    :param time_period:
    :return:
    """
    rdns = ReverseDNS()
    # Loads reverse DNS information from a JSON file found at REVERSE_DNS_FP
    rdns.update_from_json_file(REVERSE_DNS_FP)
    rdns_query = rdns.query

    print("Acquiring traceroute tests... ")

    traceroute_metadata = acquire_traceroute_tests(ps_node_urls=perfsonar_ma_url,
                                                   rdns_query=rdns_query,
                                                   test_time_range=time_period)

    ps_trace = PsTrace(PREVIOUS_ROUTE_FP, THRESHOLD, J2_EMAIL_TEMPLATE_FP)
    ps_analysis = ps_trace.analysis

    source = set()
    destination = set()
    matrix = {}
    for traceroute_test in traceroute_metadata:
        results = ps_analysis(traceroute_test, HTML_DIR, J2_TRACEROUTE_WEB_PAGE_FP)
        source.add(results[0])
        destination.add(results[1])
        matrix.setdefault(results[0], {}).setdefault(results[1], results[2])
    destination = sorted(list(destination))
    source = sorted(list(source))

    if not matrix:
        print('No valid PerfSONAR Traceroute Measurement Archive(s)! Exiting...')
        exit()

    if EMAIL_ALERTS and ps_trace.route_comparison.changed_routes:
        ps_trace.route_comparison.send_email_alert(EMAIL_TO, EMAIL_FROM, EMAIL_SUBJECT, SMTP_SERVER)

    with open(DASHBOARD_WEB_PAGE_FP, "w") as web_matrix_file:
        current_time = datetime.datetime.now().strftime("%c")
        matrix_page = Jinja2Template(J2_MATRIX_WEB_PAGE_FP)
        html_matrix_table = create_matrix_html(source, destination, matrix, rdns_query)
        web_matrix_file.write(matrix_page.render_template_output(matrix=html_matrix_table, end_date=current_time))

    # Dictionary + file path for data_store, rdns and route_comparison
    data_to_save = ((ps_trace.force_graph, FORCE_GRAPH_DATA_FP),
                    (rdns, REVERSE_DNS_FP),
                    (ps_trace.route_comparison, PREVIOUS_ROUTE_FP))

    for objects, file_path in data_to_save:
        objects.save_as_json_file(file_path)
    print("Done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--time_period', '-t', help='Time period (in seconds) from current point in time. '
                                                    'e.g. 1 day == 86400', type=int)
    parser.add_argument('--perfsonar_urls', '-u', nargs='+', help='IP or base domain of the PerfSONAR MA')

    args = parser.parse_args()
    if args.time_period < TESTING_PERIOD:
        print("ERROR: Time period (%d seconds) is less than the traceroute testing period (%d seconds)."
              "\nExiting..." % (args.time_period, TESTING_PERIOD))
        exit()
    main(args.perfsonar_urls, args.time_period)
