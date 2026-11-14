from clientmagnet.reports import pdf_bytes
from clientmagnet.audit import audit_page
from clientmagnet.sample import SAMPLE_HTML, SAMPLE_URL
from clientmagnet.store import Store


def test_pdf_contains_real_pages():
    p=pdf_bytes(audit_page(SAMPLE_URL, SAMPLE_HTML))
    assert p.startswith(b'%PDF')
    assert b'%%EOF' in p[-80:]
    assert len(p)>2000


def test_pdf_dangerous_html_as_data_not_markup():
    fake='<title>A & B <garbage></title><img alt="no" />'
    p=pdf_bytes(audit_page('https://example.org',fake))
    assert p.startswith(b'%PDF')


def test_store_persists_reports_and_leads(tmp_path):
    db=Store(tmp_path/'reports.sqlite')
    report=audit_page(SAMPLE_URL,SAMPLE_HTML)
    db.save_audit(report)
    assert db.get_audit(report['id'])['scores']==report['scores']
    assert len(db.list_audits())==1
    assert db.stats()['saved_audits']==1
    assert db.stats()['consenting_leads']==0
    out=db.add_lead(name='Test',email='test@example.org',website='',interest='Consultation')
    assert out['received']
    assert db.stats()['consenting_leads']==1
    assert db.leads()[0]['name']=='Test'
