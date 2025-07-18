from flask import Flask, jsonify, request
from flask_cors import CORS
from data import get_all_data, get_domain_by_id, update_feature_status

app = Flask(__name__)
CORS(app)

@app.route('/api/features', methods=['GET'])
def get_features():
    """
    API endpoint to get all feature data.
    """
    return jsonify(get_all_data())

@app.route('/api/features/<string:domain_id>', methods=['GET'])
def get_domain(domain_id):
    """
    API endpoint to get a single domain by its ID.
    """
    domain = get_domain_by_id(domain_id)
    if domain:
        return jsonify(domain)
    return jsonify({"error": "Domain not found"}), 404

@app.route('/api/features/<string:domain_id>/<string:feature_id>', methods=['PUT'])
def update_feature(domain_id, feature_id):
    """
    API endpoint to update the status of a feature.
    """
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "New status not provided"}), 400

    if update_feature_status(domain_id, feature_id, new_status):
        return jsonify({"message": "Feature status updated successfully"})
    return jsonify({"error": "Feature or domain not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)
