from typing import Dict, List, Type

from sa_config import PENALTY_LIST, REMOVE_THRESHOLD
from muon_frost_py.common.pyfrost.tss import TSS

from web3 import Web3

import time
import json
import numpy as np


class NodePenalty:
    def __init__(self, id: str) -> None:
        self.id = id
        self.__time = 0
        self.__weight = 0

    def add_penalty(self, error_type: str) -> None:
        self.__time = int(time.time())
        self.__weight += PENALTY_LIST[error_type]

    def get_score(self) -> int:
        current_time = int(time.time())
        return self.__weight * np.exp(self.__time - current_time)



class NodeEvaluator:
    def __init__(self) -> None:
        self.penalties: Dict[str, NodePenalty] = {}

    def get_new_party(self, old_party: List[str], n: int=None) -> List[str]:       
        below_threshold = 0
        for peer_id in old_party:
            if peer_id not in self.penalties.keys():
                self.penalties[peer_id] = NodePenalty(peer_id)
            if self.penalties[peer_id].get_score() < REMOVE_THRESHOLD:
                below_threshold += 1

        
        score_party = sorted(old_party, 
                       key=lambda x: self.penalties[x].get_score(), 
                       reverse=True)
        
        if n is None or n >= len(old_party) - below_threshold:
            n = len(old_party) - below_threshold
        
        res = score_party[:n]
        return score_party[:n]

    def evaluate_responses(self, responses: Dict[str, Dict]) -> bool:
        is_complete = True
        guilty_peer_ids = {}
        for peer_id, data in responses.items():
            data_status = data['status']
            guilty_id = None
            if data_status != 'SUCCESSFUL':
                is_complete = False
    
            if data_status in ['TIMEOUT', 'MALICIOUS']:
                guilty_id = peer_id
            
            if guilty_id is not None:
                
                if not self.penalties.get(guilty_id):
                    self.penalties[guilty_id] = NodePenalty(peer_id)
                self.penalties[guilty_id].add_penalty(data_status)
                guilty_peer_ids[guilty_id] = (data_status, self.penalties[guilty_id].get_score())

        return is_complete
