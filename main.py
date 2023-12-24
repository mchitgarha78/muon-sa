import trio
from multiprocessing import Process
from abstract.node_info import NodeInfo
from pyfrost.network.sa import SA
from libp2p.host.host_interface import IHost
from node_evaluator import NodeEvaluator
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from libp2p.crypto.secp256k1 import create_new_key_pair
from libp2p.peer.id import ID as PeerID
import logging
import os
import sys
from typing import Dict
import requests


app = Flask(__name__)


@app.route('/v1/', methods=['POST'])
def request_sign():
    muon_sa: MuonSA = app.config['SA']
    try:
        data = request.get_json()
        app_name = data.get('app')
        method_name = data.get('method')
        req_id = data.get('reqId')
        params = data.get('data', {}).get('params')
        result = data.get('data', {}).get('result')
        if None in [app_name, method_name, req_id, params, result]:
            return jsonify({'error': 'Invalid request format'}), 400

        dkg_ids = [key for key, value in muon_sa.dkg_list.items()
                   if value['app_name'] == app_name]
        if len(dkg_ids) == 0:
            return jsonify({'error': 'App not found on the apps list.'}), 400
        dkg_id = dkg_ids[0]
        response_data = trio.run(
            lambda: muon_sa.request_signature(muon_sa.dkg_list[dkg_id]['dkg_key'], muon_sa.nonces,
                                              data)
        )
        muon_sa.node_evaluator.evaluate_responses(response_data)
        return jsonify(response_data), 200
    except Exception as e:
        logging.error(
            f'Flask request_sign => Exception occurred: {type(e).__name__}: {e}')
        return jsonify({'error': 'Internal server error.'}), 500


class MuonSA(SA):
    def __init__(self, registry_url: str, address: Dict[str, str], secret: str, node_info: NodeInfo,
                 max_workers: int = 0, default_timeout: int = 50, host: IHost = None) -> None:
        
        super().__init__(address, secret, node_info,
                         max_workers, default_timeout, host)
        self.registry_url = registry_url
        self.nonces: Dict[str, list[Dict]] = {}
        self.node_evaluator = NodeEvaluator()
        self.dkg_list: Dict = {}

    async def maintain_nonces(self, min_number_of_nonces: int = 10, sleep_time: int = 2):
        while True:
            peer_ids = self.node_info.get_all_nodes()

            # TODO: Random selection
            selected_nodes = {}
            for node_id, peer_ids in peer_ids.items():
                selected_nodes[node_id] = peer_ids[0]

            nonces_response = await self.request_nonces(selected_nodes, min_number_of_nonces)
            self.node_evaluator.evaluate_responses(nonces_response)
            for node_id, peer_id in selected_nodes.items():
                if nonces_response[peer_id]['status'] == 'SUCCESSFUL':
                    self.nonces[peer_id] += nonces_response[peer_id]['nonces']
            await trio.sleep(sleep_time)

    async def maintain_dkg_list(self):
        while True:
            try:
                new_data: Dict = requests.get(self.registry_url).json()

                for id, data in new_data.items():
                    self.dkg_list[id] = data
                await trio.sleep(5 * 60)  # wait for 5 mins
            except Exception as e:
                logging.error(
                    f'Muon SA => Exception occurred: {type(e).__name__}: {e}')
                await trio.sleep(0.5)
                continue

    async def run_process(self) -> None:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.run)
            nursery.start_soon(self.maintain_nonces)
            nursery.start_soon(self.maintain_dkg_list)


if __name__ == '__main__':

    file_path = 'logs'
    file_name = 'sa.log'
    log_formatter = logging.Formatter('%(asctime)s - %(message)s', )
    root_logger = logging.getLogger()
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    with open(f'{file_path}/{file_name}', 'w'):
        pass
    file_handler = logging.FileHandler(f'{file_path}/{file_name}')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    registry_url = sys.argv[2]
    node_info = NodeInfo()
    load_dotenv()
    secret = bytes.fromhex(os.getenv('PRIVATE_KEY'))
    key_pair = create_new_key_pair(secret)
    peer_id: PeerID = PeerID.from_pubkey(key_pair.public_key)
    print(
        f'Public Key: {key_pair.public_key.serialize().hex()}, PeerId: {peer_id.to_base58()}')
    address = {
        'public_key': key_pair.public_key.serialize().hex(),
        'ip': '0.0.0.0',
        'port': str(os.getenv('PORT'))
    }
    muon_sa = MuonSA(registry_url,
                     address, os.getenv('PRIVATE_KEY'), node_info)

    # TODO: Use WSGI or uvicorn
    app.config['SA'] = muon_sa
    flask_process = Process(target=lambda: app.run(
        debug=True, use_reloader=False))
    sa_process = Process(target=lambda: trio.run(muon_sa.run_process))

    flask_process.start()
    sa_process.start()

    flask_process.join()
    sa_process.join()
