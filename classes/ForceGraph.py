class ForceGraph:
    def __init__(self):
        self.force_graph = []

    def create_force_nodes(self, hop_details, previous_hop, destination_ip):
        """
        
        :param hop_details: 
        :param previous_hop: 
        :param destination_ip: 
        :return: 
        """
        value = "end" if hop_details[1]["ip"] == destination_ip else "null"
        size = 15 if hop_details[0] == 0 else 7

        self.force_graph.append({"source": previous_hop,
                                 "target": hop_details[1]["domain"],
                                 "type": hop_details[1]["status"],
                                 "size": size,
                                 "value": value})

    def retrieve_graph(self):
        return self.force_graph
