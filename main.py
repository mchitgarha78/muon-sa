import trio
from quart_trio import QuartTrio
from quart import request, jsonify
import os
import logging
from dotenv import load_dotenv
from abstract.node_info import NodeInfo
from pyfrost.network.sa import SA
from libp2p.host.host_interface import IHost
from node_evaluator import NodeEvaluator
from libp2p.crypto.secp256k1 import create_new_key_pair
from libp2p.peer.id import ID as PeerID
from typing import Dict
from config import APPS_LIST_URL
import requests


app = QuartTrio(__name__)


@app.route('/v1/', methods=['POST'])
async def request_sign():
    muon_sa: MuonSA = app.config['SA']
    try:
        data = await request.get_json()
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
        nonces_dict = {}

        nonces_dict = {}
        for node_id in muon_sa.dkg_list[dkg_id]['party'].keys():
            nonces_dict[node_id] = muon_sa.nonces[node_id].pop()

        dkg_key = muon_sa.dkg_list[dkg_id].copy()
        dkg_key['dkg_id'] = dkg_id

        response_data = await muon_sa.request_signature(dkg_key, nonces_dict,
                                                        data, muon_sa.dkg_list[dkg_id]['party'])
        # TODO: Add response output to request signature: muon_sa.node_evaluator.evaluate_responses(response_data)
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

    async def maintain_nonces(self, min_number_of_nonces: int = 10, sleep_time: int = 10):
        while True:
            peer_ids = self.node_info.get_all_nodes()

            # TODO: Random selection
            selected_nodes = {}
            for node_id, peer_ids in peer_ids.items():
                self.nonces.setdefault(node_id, [])
                if len(self.nonces[node_id]) >= min_number_of_nonces:
                    continue
                selected_nodes[node_id] = peer_ids[0]

            nonces_response = await self.request_nonces(selected_nodes, min_number_of_nonces)
            self.node_evaluator.evaluate_responses(nonces_response)
            for node_id, peer_id in selected_nodes.items():
                if nonces_response[peer_id]['status'] == 'SUCCESSFUL':
                    self.nonces[node_id] += nonces_response[peer_id]['nonces']
            await trio.sleep(sleep_time)

    async def maintain_dkg_list(self):
        while True:
            try:
                new_data: Dict = requests.get(self.registry_url).json()

                for id, data in new_data.items():
                    self.dkg_list[id] = data
                await trio.sleep(5)  # wait for 5 mins
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


async def run_flask_app():
    await app.run_task(debug=True, host=str(os.getenv('API_HOST')), port=str(os.getenv('API_PORT')))


async def run_process(muon_sa):
    async with trio.open_nursery() as nursery:
        nursery.start_soon(run_flask_app)
        nursery.start_soon(muon_sa.run_process)

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
    root_logger.setLevel(logging.INFO)
    node_info = NodeInfo()
    load_dotenv()
    secret = bytes.fromhex(os.getenv('PRIVATE_KEY'))
    key_pair = create_new_key_pair(secret)
    peer_id: PeerID = PeerID.from_pubkey(key_pair.public_key)
    print(
        f'Public Key: {key_pair.public_key.serialize().hex()}, PeerId: {peer_id.to_base58()}')
    address = {
        'public_key': key_pair.public_key.serialize().hex(),
        'ip': str(os.getenv('HOST')),
        'port': str(os.getenv('PORT'))
    }
    muon_sa = MuonSA(APPS_LIST_URL,
                     address, os.getenv('PRIVATE_KEY'), node_info)
    app.config['SA'] = muon_sa
    # TODO: Use WSGI or uvicorn
    trio.run(run_process, muon_sa)
