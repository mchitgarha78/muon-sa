from flask import Flask, request, jsonify
from common.sa_data_manager import SADataManager
import logging
app = Flask(__name__)

data_manager = SADataManager()
# Set a secret key for the application
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route('/v1/', methods=['GET'])
def request_sign():
    try:
        data = request.get_json()
        app_name = data.get('app')
        method_name = data.get('method')
        req_id = data.get('reqId')
        params = data.get('data', {}).get('params')
        result = data.get('data', {}).get('result')
        if None in [app_name, method_name, req_id, params, result]:
            return jsonify({'error': 'Invalid request format'}), 400
        
        # TODO: handle types of potentially errors.
        # app.config['SA'].request_signature(dkg_key: Dict, sign_party_num: int, 
        #                         app_request_id: str, app_method: str, 
        #                         app_params: Dict, app_sign_params: Dict, 
        #                         app_hash: str, app_result: Dict)
        
        response_data = {
            'app': app_name,
            'method': method_name,
            'reqId': req_id,
            'params': params,
            'result': result
        }
        return jsonify(response_data), 200
    except Exception as e:
        logging.error(f'Flask request_sign => Exception occurred: {type(e).__name__}: {e}')
        return jsonify({'error': 'Internal server error.'}), 500