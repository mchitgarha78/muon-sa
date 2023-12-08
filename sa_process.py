from muon_frost_py.sa.sa import SA
from sa_config import PRIVATE, SA_DATA
from node_evaluator import NodeEvaluator
from common.sa_node_info import SANodeInfo
from typing import List, Dict
from muon_frost_py.common.utils import Utils
import sys

import trio
import logging

class SAProcess:
    def __init__(self, sa_id: str, total_node_number: int, registry_url: str) -> None:
        self.node_info = SANodeInfo()
        self.total_node_number = total_node_number
        self.registry_url = registry_url
        self.sa = SA(SA_DATA, PRIVATE, 
                               self.node_info, 0, 50)
        self.__nonces: Dict[str, list[Dict]] = {} 
        self.node_evaluator = NodeEvaluator()
        self.dkg_list: Dict = {}

    async def maintain_nonces(self, min_number_of_nonces: int = 10, sleep_time: int = 2):
        while True:
            peer_ids = self.node_info.get_all_nodes(self.total_node_number)
            for peer_id in peer_ids:
                self.__nonces.setdefault(peer_id, [])
                nonces = await self.sa.request_nonce(peer_id, min_number_of_nonces * 10)
                self.node_evaluator.evaluate_responses(nonces)
                if nonces[peer_id]['status'] == 'SUCCESSFUL':
                    self.__nonces[peer_id] += nonces[peer_id]['nonces']
            await trio.sleep(sleep_time)

    
    async def maintain_dkg_list(self):
        while True:
            new_data: Dict = Utils.get_request(self.registry_url)
            if not new_data:
                await trio.sleep(0.5)
                continue
            for id, data in new_data.items():
                self.dkg_list[id] = data
            await trio.sleep(5 * 60) # wait for 5 mins
    
    async def get_commitments(self, party: List[str], timeout: int = 5) -> Dict:
        commitments_dict = {}
        peer_ids_with_timeout = {}
        for peer_id in party:
            with trio.move_on_after(timeout) as cancel_scope:
                while not self.__nonces.get(peer_id):
                    await trio.sleep(0.1)
                
                commitment = self.__nonces[peer_id].pop()
                commitments_dict[peer_id] = commitment
        
            if cancel_scope.cancelled_caught:
                timeout_response = {
                    "status": "TIMEOUT",
                    "error": "Communication timed out",
                }
                peer_ids_with_timeout[peer_id] = timeout_response
        if len(peer_ids_with_timeout) > 0:
            self.node_evaluator.evaluate_responses(peer_ids_with_timeout)
            logging.warning(f'get_commitments => Timeout error occurred. peer ids with timeout: {peer_ids_with_timeout}')
        return commitments_dict

    async def run(self) -> None:
        async with trio.open_nursery() as nursery:
            # Start SA and maintain nonce values for each peer
            nursery.start_soon(self.sa.run)
            nursery.start_soon(self.maintain_nonces)
            nursery.start_soon(self.maintain_dkg_list)
