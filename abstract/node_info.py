from pyfrost.network.abstract import NodeInfo as BaseNodeInfo
from typing import Dict
from itertools import islice
import json

class NodeInfo(BaseNodeInfo):
    def __init__(self):
        with open('./abstract/nodes.json', 'r') as reader:
            self.nodes = json.loads(reader.read())

    def lookup_node(self, peer_id: str, node_id: str = None):
        if node_id is None:
            for node_id, data in self.nodes.items():
                result = data.get(peer_id, None)
                if result is not None:
                    return result, node_id
            return None
        return self.nodes.get(node_id, {}).get(peer_id, None), node_id

    def get_all_nodes(self, n: int = None) -> Dict:
        if n is None:
            n = len(self.nodes)
        result = {}
        for node, data in islice(self.nodes.items(), n):
            result[node] = list(data.keys())
        return result
