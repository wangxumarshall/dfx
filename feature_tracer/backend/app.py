from flask import Flask, jsonify
from flask_cors import CORS
from data import get_all_data

app = Flask(__name__)
CORS(app)

@app.route('/api/features', methods=['GET'])
def get_features():
    """
    API endpoint to get all feature data.
    """
    return jsonify(get_all_data())

if __name__ == '__main__':
    app.run(debug=True, port=5001)
