import json
import struct
import tempfile
import unittest
from pathlib import Path
from catalog import compile_catalog, fnv1a, load_catalog


class CatalogTests(unittest.TestCase):
    def load(self, messages, **options):
        data = dict(language='test', name='Test language', font='', messages=messages)
        data.update(options)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            return load_catalog(path)

    def test_two_languages_same_source(self):
        for text in ('中文', 'Deutsch', 'Polski'):
            data = compile_catalog(self.load([dict(source='Menu', translation=text)]))
            self.assertEqual(struct.unpack_from('<4sI', data), (b'MLLG', 2))
            h, key, value = struct.unpack_from('<3I', data, 20)
            self.assertEqual(h, fnv1a('Menu'))
            self.assertIn(b'Menu\0', data)
            self.assertIn(text.encode() + b'\0', data)

    def test_no_output_for_untranslated(self):
        data = compile_catalog(self.load([dict(source='Menu', translation='')]))
        self.assertEqual(len(data), 20)

    def test_reject_argument_type_change(self):
        for original, translated in [('ISO %d', 'ISO %s'), ('%s %d', '%d %s'), ('%02d', '%n'), ('%d', '%1$d')]:
            with self.assertRaises(ValueError):
                self.load([dict(source=original, translation=translated)])

    def test_reject_invalid_inputs(self):
        for messages in ([dict(source='A\0B', translation='x')], [dict(source='A', translation='x')] * 2):
            with self.assertRaises(ValueError):
                self.load(messages)
        with self.assertRaises(ValueError):
            self.load([], language='../bad')

    def test_portable_resource_filenames(self):
        self.load([], language='abcdefgh', font='lat_ext')
        for options in ({'language': 'abcdefghi'}, {'font': 'latin_ext'}):
            with self.assertRaises(ValueError):
                self.load([], **options)

    def test_literal_percentage_help(self):
        self.load([dict(source='Wait for 2% discharge.', translation='等待放电 2%。', format=False)])
        with self.assertRaises(ValueError):
            self.load([dict(source='ISO %d', translation='ISO %s', format='false')])


if __name__ == '__main__':
    unittest.main()
