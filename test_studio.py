import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from studio import lesson, slide
from publish import publish


class StudioTests(unittest.TestCase):
    def test_all_families_render(self):
        seen=set()
        for seed in range(50):
            title,tag,scenes=lesson(random.Random(seed))
            self.assertEqual(len(scenes),4)
            if tag not in seen:
                for i,(symbol,text) in enumerate(scenes):
                    self.assertEqual(slide(i,title,symbol,text,None).size,(720,1280))
                seen.add(tag)
        self.assertEqual(len(seen),3)

    @patch.dict('os.environ',{'FB_PAGE_ID':'123','FB_PAGE_TOKEN':'test'})
    @patch('requests.post')
    def test_publication_receipt(self,post):
        with tempfile.TemporaryDirectory() as path:
            job=Path(path); (job/'lesson.mp4').touch()
            (job/'metadata.json').write_text(json.dumps({'title':'demo','description':'demo'}))
            post.return_value.json.return_value={'id':'abc'}
            publish(job,'facebook'); publish(job,'facebook'); post.assert_called_once()
            self.assertEqual(json.loads((job/'facebook.json').read_text())['id'],'abc')

    @patch.dict('os.environ',{'FB_PAGE_ID':'123','FB_PAGE_TOKEN':'test'})
    @patch('requests.post',side_effect=TimeoutError)
    def test_ambiguous_upload_is_not_repeated(self,post):
        with tempfile.TemporaryDirectory() as path:
            job=Path(path); (job/'lesson.mp4').touch()
            (job/'metadata.json').write_text(json.dumps({'title':'demo','description':'demo'}))
            with self.assertRaises(TimeoutError): publish(job,'facebook')
            with self.assertRaisesRegex(RuntimeError,'Check the platform'): publish(job,'facebook')
            post.assert_called_once()
