#!/usr/bin/python3
"""
TODO: Add Description
"""

from classes.base import DataStore

__author__ = "Simon Peter Green"
__copyright__ = "Copyright (c) 2017 spgreen"
__credits__ = []
__license__ = "MIT"
__version__ = "0.5"
__maintainer__ = "Simon Peter Green"
__email__ = "simonpetergreen@singaren.net.sg"
__status__ = "Development"


class ForceGraph(DataStore):
    """
    Creates the data required for the D3.js Force Graph used within  the matrix.html.j2 template.
    It saves each hop and its information as a dict which is then appended to the force graph list.
    Force graph list example:
        [
            {
                "target": "et-1-0-0.singaren.net.sg",
                "source": "owamp.singaren.net.sg",
                "node_point": "source",
                "type": "okay"
            },
            {
                "target": "sg-mx60.jp.apan.net",
                "source": "et-1-0-0.singaren.net.sg",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "hk-mx60.jp.apan.net",
                "source": "sg-mx60.jp.apan.net",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "cuhk.hkix.net",
                "source": "hk-mx60.jp.apan.net",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "et-0-2-1-cuhk.hkix.net",
                "source": "cuhk.hkix.net",
                "node_point": "",
                "type": "okay"
            },
            {
                "target": "ps1.cuhk.edu.hk",
                "source": "et-0-2-1-cuhk.hkix.net",
                "node_point": "destination",
                "type": "okay"
            }
        ]
    """
    def __init__(self):
        """
        Initialises the list for storing force graph dictionaries used for D3.js
        found within the matrix.html.j2 template.
        """
        DataStore.__init__(self)
        self.data_store = []

    def update_from_json_file(self, file_path):
        """
        :param file_path:
        :return:
        """
        raise AttributeError("'ForceGraph' object has no attribute 'update_from_json_file'")

    def create_force_nodes(self, hop_details, previous_hop, source_ip, destination_ip):
        """
        Creates a force node dictionary entry which will be appended to the force graph list.
        Example dictionary:
            {
                "target": "et-1-0-0.singaren.net.sg",
                "source": "owamp.singaren.net.sg",
                "node_point": "source",
                "type": "okay"
            }

        :param hop_details: Nested dictionary in list or single dict of trace route hop information
        :type hop_details: list or dict
        :param previous_hop: Singular entry or list. If list it will be the route starting
                             at the source ip
        :type previous_hop: list or str
        :param destination_ip: Trace route destination IP address
        :type destination_ip: str
        :return: None
        """
        if len(hop_details) != len(previous_hop):
            print("Error: Hop information and previous hop list are of different length!")
            return

        unique_tag = 'null tag:{index}_%s_%s' % (source_ip, destination_ip)
        for index, hop in enumerate(hop_details):
            node_point = ""
            if hop.get("ip") == destination_ip:
                node_point = "destination"
            elif index == 0:
                node_point = "source"

            source = unique_tag.format(index=index) if '*' in previous_hop[index] else previous_hop[index]
            target = unique_tag.format(index=index+1) if '*' in hop['hostname'] else hop['hostname']
            self.data_store.append({"source": source,
                                    "target": target,
                                    "type": hop["status"],
                                    "node_point": node_point})
