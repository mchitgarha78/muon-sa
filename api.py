from flask import Flask, request, jsonify
from common.sa_data_manager import SADataManager
from sa_process import SAProcess
import trio
import logging
app = Flask(__name__)

data_manager = SADataManager()
# Set a secret key for the application
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route('/v1/', methods=['POST'])
def request_sign():
    sa_process: SAProcess = app.config['SA']
    try:
        data = request.get_json()
        app_name = data.get('app')
        method_name = data.get('method')
        req_id = data.get('reqId')
        params = data.get('data', {}).get('params')
        result = data.get('data', {}).get('result')
        if None in [app_name, method_name, req_id, params, result]:
            return jsonify({'error': 'Invalid request format'}), 400
        
        dkg_ids = [key for key, value in sa_process.dkg_list.items() if value['app_name'] == app_name]
        if len(dkg_ids) == 0:
            return jsonify({'error': 'App not found on the node.'}), 400
        dkg_id = dkg_ids[0]
        commitments_dict = trio.run(
                           lambda: sa_process.get_commitments(sa_process.dkg_list[dkg_id]['party'])
        )
        response_data = trio.run(
                        lambda: sa_process.sa.request_signature(sa_process.dkg_list[dkg_id]['dkg_key'], commitments_dict,
                        data)
        )
        
        return jsonify(response_data), 200
    except Exception as e:
        logging.error(f'Flask request_sign => Exception occurred: {type(e).__name__}: {e}')
        return jsonify({'error': 'Internal server error.'}), 500