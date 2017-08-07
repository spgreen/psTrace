class ForceGraph:
    def __init__(self):
        """
        Initialises the list for storing force graph dictionaries used for D3.js 
        found within the matrix.html.j2 template.
        """
        self.force_graph = []

    def create_force_nodes(self, hop_details, previous_hop, destination_ip):
        """
        Creates the force node dictionary entry that will be appended to the force graph list.
        :param hop_details: Nested dictionary in list or single dictionary of trace route hop information 
        :type hop_details: list or dict
        :param previous_hop: Singular entry or list. If list it will be the route starting at the source ip
        :type previous_hop: list or str
        :param destination_ip: Trace route destination IP address
        :type destination_ip: str
        :return: 
        """
        if not isinstance(hop_details, list):
            hop_details = [hop_details]
        if not isinstance(previous_hop, list):
            previous_hop = [previous_hop]

        if len(hop_details) != len(previous_hop):
            return

        for i in range(len(hop_details)):
            node_point = ""
            if hop_details[i]["ip"] == destination_ip:
                node_point = "destination"
            elif i == 0:
                node_point = "source"

            self.force_graph.append({"source": previous_hop[i],
                                     "target": hop_details[i]["domain"],
                                     "type": hop_details[i]["status"],
                                     "node_point": node_point})

    def retrieve_graph(self):
        """
        :return: dict; current force graph list state 
        """
        return self.force_graph
