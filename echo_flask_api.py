from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['POST'])
def echo():
    payload = request.get_json(force=True)
    app.logger.info(f"Received payload: {payload}")
    return jsonify(payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
