from flask import Flask, request, jsonify
from muon_sa import MuonSA
import trio
import logging
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
