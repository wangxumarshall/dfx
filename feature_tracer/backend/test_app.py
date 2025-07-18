import unittest
import json
from app import app

class FeatureTracerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

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

if __name__ == '__main__':
    unittest.main()
