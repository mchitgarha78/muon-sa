from muon_frost_py.sa.sa import SA
from sa_config import PRIVATE
from node_evaluator import NodePenalty, NodeEvaluator
from common.sa_data_manager import SADataManager
from common.sa_dns import SADns
from typing import List

import sys

import trio
import logging

class SAProcess:
    def __init__(self, sa_id: str, total_node_number: int) -> None:
        dns = SADns()
        all_nodes = dns.get_all_nodes(total_node_number)
        
        data_manager = SADataManager()
        
        registry_url = ''

        self.sa = SA(dns.lookup_sa(sa_id), PRIVATE, 
                               dns, data_manager, NodePenalty, NodeEvaluator, registry_url, 0, 50)
        
    async def run(self) -> None:
        async with trio.open_nursery() as nursery:
            # Start SA and maintain nonce values for each peer
            nursery.start_soon(self.sa.run)

            nursery.start_soon(self.sa.maintain_nonces)
            
            nursery.start_soon(self.sa.maintain_dkg_list)


