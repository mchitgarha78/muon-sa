from typing import Dict, List, Type
from muon_frost_py.abstract.sa.node_evaluator import Evaluator, Penalty
from muon_frost_py.abstract.data_manager import DataManager

from sa_config import PENALTY_LIST, REMOVE_THRESHOLD
from muon_frost_py.common.TSS.tss import TSS

from web3 import Web3

import time
import json
import numpy as np


class NodePenalty(Penalty):
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



class NodeEvaluator(Evaluator):
    def __init__(self, data_manager: DataManager, penalty_class_type: NodePenalty) -> None:
        super().__init__(data_manager, penalty_class_type)
        
        self.penalties: Dict[str, self.penalty_class_type] = {}

    def get_new_party(self, table_name: str,key: str, old_party: List[str], n: int=None) -> List[str]:       
        below_threshold = 0
        for peer_id in old_party:
            if peer_id not in self.penalties.keys():
                self.penalties[peer_id] = Penalty(peer_id)
            if self.penalties[peer_id].get_score() < REMOVE_THRESHOLD:
                below_threshold += 1

        
        score_party = sorted(old_party, 
                       key=lambda x: self.penalties[x].get_score(), 
                       reverse=True)
        
        if n is None or n >= len(old_party) - below_threshold:
            n = len(old_party) - below_threshold
        
        res = score_party[:n]
        self.data_manager.add_data(table_name, key,res)
        return score_party[:n]

    def evaluate_responses(self, table_name: str, key: str, responses: Dict[str, Dict]) -> bool:
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
                    self.penalties[guilty_id] = Penalty(peer_id)
                self.penalties[guilty_id].add_penalty(data_status)
                guilty_peer_ids[guilty_id] = (data_status, self.penalties[guilty_id].get_score())

        res = {
            'guilty_peer_ids' : guilty_peer_ids,
            'responses' : responses,
        }
        self.data_manager.add_data(table_name, key, res)        
        return is_complete

    def evaluate_dkg(self, table_name: str, key: str, responses: Dict[str, Dict], round1_response: Dict = None, round2_response: Dict = None):
        pass

    
    def exclude_complaint(self, complaint: Dict, public_keys: Dict, round1_response: Dict, round2_response: Dict):
        complaint_pop_hash = Web3.solidity_keccak(
            [
                "uint8", 
                "uint8", 
                "uint8", 
                "uint8",
                "uint8"
                ],
            [
                public_keys[complaint['complaintant']],
                public_keys[complaint['malicious']],
                complaint['encryption_key'],
                complaint['public_nonce'],
                complaint['commitment']
                ],
            )
        pop_verification = TSS.complaint_verify(
            TSS.code_to_pub(public_keys[complaint['complaintant']]),
            TSS.code_to_pub(public_keys[complaint['malicious']]),
            TSS.code_to_pub(complaint['encryption_key']),
            complaint['proof'],
            complaint_pop_hash
        )
        
        if not pop_verification:
            return complaint['complaintant']
        
        encryption_key = TSS.generate_hkdf_key(complaint['encryption_key'])
        encrypted_data = b'' # TODO
        data = json.loads(TSS.decrypt(encrypted_data, encryption_key))

        for data in round1_response.values():
            round1_data = data['broadcast']
            if round1_data["sender_id"] == complaint['complaintant']:
                public_fx = round1_data["public_fx"]

                point1 = TSS.calc_poly_point(
                    list(map(TSS.code_to_pub, public_fx)),
                    int.from_bytes(self.node_id.to_bytes(), 'big')
                )
                
                point2 = TSS.curve.mul_point(
                    data["f"], 
                    TSS.curve.generator
                )

                if point1 != point2:
                    return complaint['malicious']
                else:
                    return complaint['complaintant']