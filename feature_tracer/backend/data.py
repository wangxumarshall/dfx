import json

import pandas as pd
import json

def get_all_data():
    """
    Reads data from the Excel file and returns it in the desired format.
    """
    try:
        domains_df = pd.read_excel('features.xlsx', sheet_name='domains')
        features_df = pd.read_excel('features.xlsx', sheet_name='features')
    except FileNotFoundError:
        return {"error": "features.xlsx not found"}

    domains = domains_df.to_dict(orient='records')
    features = features_df.to_dict(orient='records')

    for domain in domains:
        domain['features'] = [f for f in features if f['domain_id'] == domain['id']]

    # Calculate summary
    total_features = sum(d['total_features'] for d in domains)
    completed_features = sum(d['completed'] for d in domains)
    in_progress_features = sum(d['in_progress'] for d in domains)
    not_started_features = sum(d['not_started'] for d in domains)

    return {
        "summary": {
            "total_features": total_features,
            "completed_features": completed_features,
            "in_progress_features": in_progress_features,
            "not_started_features": not_started_features,
            "last_updated": "2025年7月18日 14:30" # This could be dynamic in a real app
        },
        "domains": domains
    }

def get_domain_by_id(domain_id):
    """
    Returns a single domain by its ID from the Excel file.
    """
    data = get_all_data()
    if "error" in data:
        return None
    for domain in data['domains']:
        if domain['id'] == domain_id:
            return domain
    return None

def update_feature_status(domain_id, feature_id, new_status):
    """
    Updates the status of a feature in the Excel file.
    """
    try:
        xls = pd.ExcelFile('features.xlsx')
        features_df = pd.read_excel(xls, sheet_name='features')
        domains_df = pd.read_excel(xls, sheet_name='domains')
    except FileNotFoundError:
        return False

    feature_index = features_df.index[(features_df['id'] == feature_id) & (features_df['domain_id'] == domain_id)].tolist()
    if not feature_index:
        return False

    features_df.loc[feature_index[0], 'status'] = new_status

    with pd.ExcelWriter('features.xlsx', engine='openpyxl') as writer:
        domains_df.to_excel(writer, sheet_name='domains', index=False)
        features_df.to_excel(writer, sheet_name='features', index=False)

    return True
