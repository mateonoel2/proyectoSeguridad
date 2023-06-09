from functools import wraps
import base64
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from block import Block, Blockchain
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
app = Flask(__name__)
CORS(app)

API_KEY = 'qPzT2B7AhloXs9BEgmQcoaBuMpabQO6s'

def validate_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('Authorization')
        if api_key == f'Bearer {API_KEY}':
            return func(*args, **kwargs)
        else:
            return jsonify({'error': 'Unauthorized'}), 401
    return wrapper

def parse_jwt(token):
    base64_payload = token.split('.')[1]
    base64_payload += '=' * (4 - (len(base64_payload) % 4))  
    decoded_payload = base64.urlsafe_b64decode(base64_payload).decode('utf-8')
    return json.loads(decoded_payload)

@app.route('/')
def home():
    return "ok"

blockchain = Blockchain()

users = {}

@app.route('/api/public_key/<userID>', methods=['POST'])
@validate_api_key
def get_public_key(userID): 
    token = request.get_json().get('credential')
    payload = parse_jwt(token)
    if payload['sub'] != userID:
        return "Invalid token", 400
    try:
        public_key = users[userID]
        key = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
        return key
    except:
        return "No user found", 404
    

@app.route('/api/transaction/<userID>', methods=['POST'])
@validate_api_key
def transaction(userID):
    data = request.get_json()
    sender_key = users[userID]
    sender_str = sender_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo).decode('utf-8')
    print(sender_str)

    recipient = data.get('account')
    recipient = recipient.replace("-----BEGIN PUBLIC KEY----- ", "")
    recipient = recipient.replace(" -----END PUBLIC KEY-----", "")
    recipient = recipient.strip()
    recipient = recipient.replace(" ", "\n")
    recipient = "-----BEGIN PUBLIC KEY-----\n" + recipient +  "\n-----END PUBLIC KEY-----\n"

    print(recipient)

    key_bytes = recipient.encode('utf-8')
    

    recipient_key = serialization.load_pem_public_key(key_bytes, backend=default_backend())
    amount = data.get('amount')

    if (sender_str == recipient):
        return "Cannot send to yourself", 400

    blockchain.add_transaction(sender_key, recipient_key, int(amount))
    return "Transaction added successfully"

@app.route('/api/balance/<userID>', methods=['GET'])
@validate_api_key
def get_balance(userID):
    try:
        key = users[userID]
        balance = blockchain.get_user_balance(key)
        return str(balance)
    except:
        return "No user found", 404
    
@app.route('/api/mine/<userID>', methods=['GET'])
@validate_api_key
def mine(userID):
    blockchain.mine_pending_transactions(users[userID])
    return "Block mined successfully"

@app.route('/api/create_account/<userID>', methods=['POST'])
@validate_api_key
def create_account(userID):
    user_key = blockchain.add_user()
    users[userID] = user_key    
    return "Account created successfully"

@app.route('/api/blocks', methods=['GET', 'POST'])
def blocks_route():
    if request.method == 'GET':
        # Logic to return the blockchain as JSON
        blockchain_json = jsonify(blockchain.to_json())
        return blockchain_json, 200
    elif request.method == 'POST':
        # Logic to receive and validate a new block
        data = request.get_json()

        # Extract block data from the request
        previous_hash = data.get('previous_hash')
        timestamp = data.get('timestamp')
        transactions = data.get('transactions')
        nonce = data.get('nonce')

        # Create a new block instance
        new_block = Block(previous_hash, timestamp, transactions, nonce)

        new_block.mine_block(blockchain.difficulty)

        # Validate the new block
        if new_block.is_valid():
            # Add the new block to the blockchain
            blockchain.add_block(new_block)
            response = {'message': 'New block added successfully'}
            return jsonify(response), 201
        else:
            response = {'message': 'Invalid block. Rejected.'}
            return jsonify(response), 400

if __name__ == '__main__':
    app.run(port=8080)