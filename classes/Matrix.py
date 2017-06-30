import collections
import json



class Matrix:
    def __init__(self, test_metadata):
        self.complete_matrix = self._creation(test_metadata)

    def _creation(self, test_metadata, src_node_key='source', dest_node_key='destination'):
        """
        
        :param test_metadata: 
        :param src_node_key: 
        :param dest_node_key: 
        :return: 
        """
        matrix = set()

        for singular_test in test_metadata:
            source_address = test_metadata[singular_test][src_node_key]
            destination_address = test_metadata[singular_test][dest_node_key]
            matrix.add(source_address)
            matrix.add(destination_address)

        # Changes set to a list to allow for indexing
        matrix_headers = list(matrix)
        # Creates the destination information dict for all matrix sources to all destinations - all values set to '*'.
        matrix_dict = {destination:{"rtt": "*", "status": "*", "fp_html": "*"} for destination in matrix_headers}

        json_dumps = json.dumps
        json_loads = json.loads
        # Combines destination dictionary into the source dictionary creating the final matrix
        complete_matrix = {source: json_loads(json_dumps(matrix_dict)) for source in matrix}
        return self.sort_dict_by_key(complete_matrix)


    def update(self, source="", destination="", rtt="", fp_html="", status=""):
        """
        
        :param source: 
        :param destination: 
        :param rtt: 
        :param fp_html: 
        :param status: 
        :return: 
        """
        if not rtt:
            self.complete_matrix[source][destination]["rtt"] = "psTimeout"
            return self.complete_matrix

        elif source not in self.complete_matrix.keys():
            # Used to include sources not found from the initial query"""
            return

        if self.complete_matrix[source][destination]["rtt"] == "*":
            # update matrix with rtt value
            matrix = self.complete_matrix[source][destination]
            matrix["rtt"] = rtt
            matrix["status"] = status
            matrix["fp_html"] = fp_html

    def output(self):
        return self.complete_matrix

    def sort_dict_by_key(self, unsorted_dictionary):
        """Sorts an ordinary dictionary into a sorted ordered dictionary using the OrderedDict module 
            from the collections library"""
        return collections.OrderedDict(sorted(unsorted_dictionary.items(), key=lambda i: i[0]))

#arr={'ps1.daej.kreonet2.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/22c43734dc414305ba2dcbf1c78c9f9f/', 'source': '203.30.39.11', 'destination': '210.119.23.2'}, 'perfsonar-sg.noc.tein3.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/7bbb1442654b4f71aa55c37d99748a6e/', 'source': '203.30.39.11', 'destination': '202.179.252.18'}, 'nms1.jp.apan.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/c6c47129a7d84831b0b71b0c23f07200/', 'source': '203.30.39.11', 'destination': '203.181.248.70'}, 'ps-bandwidth.atlas.unimelb.edu.au': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/35194d4e83e34e5a915a97b4815a9229/', 'source': '203.30.39.11', 'destination': '192.231.127.40'}, 'perfsonar-m1.twaren.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/f4eb7e0c14ac483786b032a703913862/', 'source': '203.30.39.11', 'destination': '211.79.61.148'}, 'perfsonar.cen.ct.gov': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/628cbf8454ed4e5bb8623b0cef7884a1/', 'source': '203.30.39.11', 'destination': '64.251.58.166'}, 'perfmum.nkn.in': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/ae6d896dfa9f4bb187ba4b9215e683ff/', 'source': '203.30.39.11', 'destination': '14.139.5.218'}, 'perfSONAR.myren.net.my': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/7827a3656b554e7c8afa9c2d83d059e9/', 'source': '203.30.39.11', 'destination': '203.80.20.66'}, 'nsw-brwy-ps1.aarnet.net.au': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/e6d8c63226094372ba2f92068e49a20e/', 'source': '203.30.39.11', 'destination': '138.44.6.146'}, 'ps1.itsc.cuhk.edu.hk': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/50efdb47f5fb4543878d40f110b2c85e/', 'source': '203.30.39.11', 'destination': '137.189.192.25'}, 'wa-knsg-ps1.aarnet.net.au': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/d7929a141dd143138900f084c9877d25/', 'source': '203.30.39.11', 'destination': '138.44.176.90'}, 'psmp-gn-owd-01-lon2-uk-v4.geant.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/00388ad2bc7f46ffbaab6a3190e33a86/', 'source': '203.30.39.11', 'destination': '62.40.104.197'}, 'test.seat.transpac.org': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/c6bb96834c1d4142b12a9bd4180d7810/', 'source': '203.30.39.11', 'destination': '192.203.115.2'}, 'perfsonar.pregi.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/3578debec4aa4840a9f7021f05cc517d/', 'source': '203.30.39.11', 'destination': '202.90.129.130'}, 'perfsonar-hk.noc.tein3.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/fb8d004ea5ff4f6580d56ff92494b4d9/', 'source': '203.30.39.11', 'destination': '202.179.246.18'}, 'psmp-gn-bw-01-lon-uk.geant.net': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/5f048d9a352d4719b52890aa90a5d62e/', 'source': '203.30.39.11', 'destination': '62.40.106.131'}, 'perfsonar.uni.net.th': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/0c14e7cf8b8c4fa5883b22c6b11db50a/', 'source': '203.30.39.11', 'destination': '202.28.194.4'}, 'ls.ntl.nectec.or.th': {'url': 'http://perfsonar-gs.singaren.net.sg/esmond/perfsonar/archive/bb89398d17b44565a275bfad8f6437dd/', 'source': '203.30.39.11', 'destination': '203.185.93.2'}}

#m = Matrix(arr)
#m.creation()
#print(m.complete_matrix)
#print(m.matrix_headers)
#m.update(source="203.30.39.11",destination="64.251.58.166", rtt="stuff")
#for (k,v) in m.complete_matrix.items():
#     print(k, v)
#print(m.complete_matrix)
