import unittest2 as unittest
import json
import py


def _create_test_app(tmp):
    from rio import create_app
    app = create_app()
    app.config['STORAGE_ENGINE'] = 'filesystem'
    app.config['STORAGE_FS_PATH'] = str((tmp/'storage').ensure(dir=True))
    return app


class FormsTest(unittest.TestCase):

    def setUp(self):
        self.tmp = py.path.local.mkdtemp()
        self.addCleanup(self.tmp.remove)
        self.app = _create_test_app(self.tmp)

    def test_minimal_add(self):
        self.doc = None
        def doc_saved(name, doc_id, doc):
            self.doc_id = doc_id
            self.doc = doc

        self.app.document_signal.connect(doc_saved, sender='save')

        client = self.app.test_client()
        form_data = {
            'section1_type': 'K',
            'section1_sitecode': 'asdfqwer3',
            'section1_date': '200503',
            'section1_site_name': 'Firul Ierbii',
            'section2_regcod_0_reg_code': '',
            'section2_regcod_0_reg_name': 'Poiana',
            'section2_regcod_0_cover': '',
            'section2_bio_region_alpine': '1',
        }
        response = client.post('/new', data=form_data, follow_redirects=True)
        self.assertIsNotNone(self.doc)
        self.assertIn("Document %r saved" % self.doc_id, response.data)

        saved_doc = json.loads((self.tmp/'storage'/'doc_0.json').read())
        section1 = saved_doc['section1']
        self.assertEqual(section1['type'], 'K')
        self.assertEqual(section1['sitecode'], 'asdfqwer3')
        self.assertEqual(section1['date'], '200503')
        self.assertEqual(section1['site_name'], 'Firul Ierbii')
        section2 = saved_doc['section2']
        self.assertIsNone(section2['regcod'][0]['reg_code'])
        self.assertEqual(section2['regcod'][0]['reg_name'], 'Poiana')
        self.assertIsNone(section2['regcod'][0]['cover'])
        self.assertTrue(section2['bio_region']['alpine'])
