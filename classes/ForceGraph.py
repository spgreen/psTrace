class ForceGraph:
    def __init__(self):
        self.force_graph = []

    def create_force_nodes(self, hop_details, previous_hop, destination_ip):
        """
        
        :param hop_details: 
        :param previous_hop: Singular entry or list. If list it will be the route starting at the source ip
        :param destination_ip: Singular entry or list. If list it will be route stats starting after the source ip
        :return: 
        """
        if type(hop_details) is not list:
            hop_details = [hop_details]
        if type(previous_hop) is not list:
            previous_hop = [previous_hop]

        if len(hop_details) != len(previous_hop):
            return

        for i in range(len(hop_details)):
            value = "end" if hop_details[i]["ip"] == destination_ip else "null"
            size = 15 if i == 0 else 7

            self.force_graph.append({"source": previous_hop[i],
                                     "target": hop_details[i]["domain"],
                                     "type": hop_details[i]["status"],
                                     "size": size,
                                     "value": value})

    def retrieve_graph(self):
        return self.force_graph
