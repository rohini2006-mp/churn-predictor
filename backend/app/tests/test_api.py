from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_customer_prediction():
    customers = client.get('/api/customers').json()['items']
    response = client.post('/api/predict', json={'customer_id': customers[0]['id']})
    assert response.status_code == 201
    body = response.json()
    assert 0 <= body['probability'] <= 1
    assert body['risk_level'] in {'low', 'medium', 'high'}
    assert body['important_factors']
