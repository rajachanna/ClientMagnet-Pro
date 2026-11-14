"""One-command reproducible synthetic website audit and lead capture."""
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient

from clientmagnet.api import create_app
from clientmagnet.config import Settings
from clientmagnet.sample import SAMPLE_HTML, SAMPLE_URL

KEY = 'clientmagnet-demo-operator-key-1234567890abcdef'


def main():
    with TemporaryDirectory(prefix='clientmagnet-demo-') as path:
        app = create_app(Settings(db_path=Path(path)/'demo.sqlite',operator_key=KEY))
        client = TestClient(app)
        auth = {'X-Operator-Key': KEY}
        print('ClientMagnet Pro — LOCAL, SYNTHETIC, NO EXTERNAL NETWORK OR MESSAGES')
        r = client.get('/api/demo')
        assert r.status_code==200
        sample = r.json()
        print('Sample score:',sample['scores']['overall'],'| checks:',sample['summary']['total'])
        r = client.post('/api/operator/audits',headers=auth,json={'url':SAMPLE_URL,'html':SAMPLE_HTML})
        assert r.status_code==200,r.text
        report = r.json()
        print('Private HTML audit:',report['id'],'| score:',report['scores']['overall'])
        pdf = client.get('/api/operator/audits/'+report['id']+'/pdf',headers=auth)
        assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
        print('PDF:',len(pdf.content),'bytes')
        no_consent = client.post('/api/leads',json={'name':'Demo Owner','email':'demo@example.org','consent':False})
        assert no_consent.status_code==422
        yes_consent = client.post('/api/leads',json={'name':'Demo Owner','email':'demo@example.org','consent':True})
        assert yes_consent.status_code==201
        print('Consent denied/accepted:',no_consent.status_code,yes_consent.status_code)
        stats=client.get('/api/operator/metrics',headers=auth)
        assert stats.status_code==200 and stats.json()['saved_audits']==1 and stats.json()['consenting_leads']==1
        assert client.post('/api/public/audit',json={'url':'https://example.org'}).status_code==403
        print('Public live fetch: safely disabled by default')
        print('PASS — offline website audit, PDF, permission-gated lead capture and metrics')


if __name__=='__main__':
    main()
