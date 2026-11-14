from clientmagnet.config import Settings
from clientmagnet.api import create_app
from clientmagnet.sample import SAMPLE_HTML, SAMPLE_URL
from fastapi.testclient import TestClient
from .conftest import AUTH
import pytest


def test_public_demo(client):
    r = client.get('/api/demo')
    assert r.status_code == 200
    assert r.json()['source'] == 'synthetic_sample'
    assert client.get('/').status_code == 200


def test_health_reports_disabled_live_scans(client):
    r=client.get('/health')
    assert r.json()['live_fetch_enabled'] is False
    assert r.json()['public_scans_enabled'] is False


def test_private_routes_require_key(client):
    for path in ('/api/operator/audits','/api/operator/leads','/api/operator/metrics'):
        assert client.get(path).status_code == 401
        assert client.get(path,headers={'X-Operator-Key':'WRONG'}).status_code == 401


def test_operator_key_not_configured_is_closed(tmp_path):
    app=create_app(Settings(db_path=tmp_path/'other.db'))
    assert TestClient(app).get('/api/operator/leads',headers={'X-Operator-Key':'guess'}).status_code==401


def test_operator_can_run_report_and_download_pdf(client):
    r=client.post('/api/operator/audits',headers=AUTH,json={'url':SAMPLE_URL,'html':SAMPLE_HTML})
    assert r.status_code==200,r.text
    rid=r.json()['id']
    assert client.get('/api/operator/audits',headers=AUTH).json()['audits'][0]['id']==rid
    assert client.get(f'/api/operator/audits/{rid}',headers=AUTH).json()['id']==rid
    pdf=client.get(f'/api/operator/audits/{rid}/pdf',headers=AUTH)
    assert pdf.status_code==200
    assert pdf.headers['content-type']=='application/pdf'
    assert pdf.content.startswith(b'%PDF')
    assert len(pdf.content)>1000


def test_operator_live_fetch_off_by_default(client):
    r=client.post('/api/operator/audits',headers=AUTH,json={'url':'https://example.org'})
    assert r.status_code==403


def test_public_live_fetch_off_by_default(client):
    r=client.post('/api/public/audit',json={'url':'https://example.org'})
    assert r.status_code==403


def test_lead_opt_in_required(client):
    obj={'name':'Morgan Silva','email':'morgan@example.org','website':'https://example.org','interest':'Business website redesign','consent':False}
    assert client.post('/api/leads',json=obj).status_code==422
    assert client.get('/api/operator/metrics',headers=AUTH).json()['consenting_leads']==0
    obj['consent']=True
    response=client.post('/api/leads',json=obj)
    assert response.status_code==201,response.text
    assert response.json()['received']
    leads=client.get('/api/operator/leads',headers=AUTH).json()['leads']
    assert leads[0]['email']=='morgan@example.org'
    assert leads[0]['consent_utc']


def test_operator_leads_cannot_be_exposed(client):
    assert client.get('/api/operator/leads').status_code ==401


def test_invalid_lead_email(client):
    obj={'name':'Morgan Silva','email':'bad_email','consent':True}
    assert client.post('/api/leads',json=obj).status_code==422


def test_lead_website_must_be_https(client):
    obj={'name':'Morgan Silva','email':'morgan@example.org','website':'http://localhost','consent':True}
    assert client.post('/api/leads',json=obj).status_code==422


def test_rate_limit_blocks_sixth_lead(client):
    obj={'name':'Morgan Silva','email':'morgan@example.org','consent':True}
    for _ in range(5):
        assert client.post('/api/leads',json=obj).status_code==201
    assert client.post('/api/leads',json=obj).status_code==429


def test_unavailable_pdf_does_not_leak_data(client):
    assert client.get('/api/operator/audits/'+'a'*32+'/pdf',headers=AUTH).status_code==404
    assert client.get('/api/operator/audits/'+'a'*32+'/pdf').status_code==401


def test_config_fails_invalid_public_scan_state(tmp_path):
    with pytest.raises(ValueError):
        create_app(Settings(db_path=tmp_path/'test.db',public_scans_enabled=True,live_fetch_enabled=False))


def test_config_blocks_operator_placeholder():
    assert not Settings(operator_key='REPLACE_WITH_STRONG_RANDOM_KEY_AT_LEAST_32_CHARACTERS').operator_ready


def test_sample_pdf_public_and_user_free(client):
    r=client.get('/api/demo/pdf')
    assert r.status_code==200
    assert r.content[:4]==b'%PDF'


def test_metrics_start_at_zero(client):
    r=client.get('/api/operator/metrics',headers=AUTH)
    assert r.status_code==200
    assert r.json()['saved_audits']==0


def test_no_script_injection_reflected_via_dashboard(client):
    page=client.get('/').text
    assert 'textContent' in page
    assert 'innerHTML' not in page
