import unittest
import json
import os
import pandas as pd
from app import app

class FeatureTracerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.excel_path = 'features.xlsx'
        self.create_test_excel()

    def tearDown(self):
        os.remove(self.excel_path)

    def create_test_excel(self):
        domains_data = {
            'id': ['memory-management'],
            'name': ['内存管理'],
            'total_features': [420],
            'completed': [328],
            'in_progress': [65],
            'not_started': [27],
            'icon': ['fa-microchip']
        }
        features_data = {
            'id': ['virtual-memory'],
            'name': ['虚拟内存管理'],
            'description': ['支持分页和分段'],
            'status': ['进行中'],
            'domain_id': ['memory-management']
        }
        with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
            pd.DataFrame(domains_data).to_excel(writer, sheet_name='domains', index=False)
            pd.DataFrame(features_data).to_excel(writer, sheet_name='features', index=False)

    def test_get_all_features(self):
        response = self.app.get('/api/features')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('summary', data)
        self.assertIn('domains', data)

    def test_get_domain_by_id(self):
        response = self.app.get('/api/features/memory-management')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], 'memory-management')
        self.assertEqual(data['name'], '内存管理')

    def test_get_domain_not_found(self):
        response = self.app.get('/api/features/non-existent-domain')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Domain not found')

    def test_update_feature_status(self):
        payload = {'status': '已完成'}
        response = self.app.put('/api/features/memory-management/virtual-memory',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Feature status updated successfully')

        # Verify the status was updated
        response = self.app.get('/api/features/memory-management')
        data = json.loads(response.data)
        feature = next(f for f in data['features'] if f['id'] == 'virtual-memory')
        self.assertEqual(feature['status'], '已完成')

    def test_update_feature_not_found(self):
        payload = {'status': '已完成'}
        response = self.app.put('/api/features/memory-management/non-existent-feature',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Feature or domain not found')

    def test_update_feature_no_status(self):
        payload = {}
        response = self.app.put('/api/features/memory-management/virtual-memory',
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'New status not provided')

    def test_download_template(self):
        response = self.app.get('/api/template')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    unittest.main()
