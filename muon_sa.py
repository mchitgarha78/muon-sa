from pyfrost.network.sa import SA
from libp2p.host.host_interface import IHost
from config import PRIVATE, SA_INFO
from node_evaluator import NodeEvaluator
from common.node_info import NodeInfo
from typing import List, Dict
import trio
import logging
import requests

class MuonSA(SA):
    def __init__(self, total_node_number: int, registry_url: str, address: Dict[str, str], secret: str, node_info: NodeInfo,
                 max_workers: int = 0, default_timeout: int = 50, host: IHost = None) -> None:
        super().__init__(address, secret, node_info,
                         max_workers, default_timeout, host)
        self.total_node_number = total_node_number
        self.registry_url = registry_url
        self.nonces: Dict[str, list[Dict]] = {}
        self.node_evaluator = NodeEvaluator()
        self.dkg_list: Dict = {}

    async def maintain_nonces(self, min_number_of_nonces: int = 10, sleep_time: int = 2):
        while True:
            peer_ids = self.node_info.get_all_nodes(self.total_node_number)
            selected_nodes = {}
            for node_id, peer_ids in peer_ids.items():
                selected_nodes[node_id] = peer_ids[0]
            # TODO: handle Exception for request nonces
            nonces = await self.request_nonces(selected_nodes, min_number_of_nonces * 10)
            self.node_evaluator.evaluate_responses(nonces)
            for peer_id in peer_ids:
                if nonces[peer_id]['status'] == 'SUCCESSFUL':
                    self.nonces[peer_id] += nonces[peer_id]['nonces']
            await trio.sleep(sleep_time)

    async def maintain_dkg_list(self):
        while True:
            try:
                new_data: Dict = requests.get(self.registry_url).json()
            
                for id, data in new_data.items():
                    self.dkg_list[id] = data
                await trio.sleep(5 * 60)  # wait for 5 mins
            except Exception as e:
                logging.error(f'Muon SA => Exception occurred: {type(e).__name__}: {e}')
                await trio.sleep(0.5)
                continue

    async def get_commitments(self, party: List[str], timeout: int = 5) -> Dict:
        commitments_dict = {}
        peer_ids_with_timeout = {}
        for peer_id in party:
            with trio.move_on_after(timeout) as cancel_scope:
                while not self.nonces.get(peer_id):
                    await trio.sleep(0.1)

                commitment = self.nonces[peer_id].pop()
                commitments_dict[peer_id] = commitment

            if cancel_scope.cancelled_caught:
                timeout_response = {
                    "status": "TIMEOUT",
                    "error": "Communication timed out",
                }
                peer_ids_with_timeout[peer_id] = timeout_response
        if len(peer_ids_with_timeout) > 0:
            self.node_evaluator.evaluate_responses(peer_ids_with_timeout)
            logging.warning(
                f'get_commitments => Timeout error occurred. peer ids with timeout: {peer_ids_with_timeout}')
        return commitments_dict

    async def run_process(self) -> None:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.run)
            nursery.start_soon(self.maintain_nonces)
            nursery.start_soon(self.maintain_dkg_list)
