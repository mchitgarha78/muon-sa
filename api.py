from flask import Flask, request, jsonify

app = Flask(__name__)

# Set a secret key for the application
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Sample data for demonstration
sample_output = {
    "users": [
        {"id": 1, "username": "john_doe"},
        {"id": 2, "username": "jane_smith"}
    ]
}

@app.route('/v1', methods=['GET'])
def request_app():
    return jsonify(sample_output['users']), 200
    #return jsonify({"error": "Username is required"}), 400
