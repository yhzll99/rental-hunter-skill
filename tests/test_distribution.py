import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT/'tools'/f'{name}.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class DistributionTests(unittest.TestCase):
    def test_packages(self):
        pack=load('package')
        with tempfile.TemporaryDirectory() as tmp:
            paths=pack.build(Path(tmp))
            self.assertEqual(len(paths),2)
            for path in paths:
                with zipfile.ZipFile(path) as z:
                    self.assertEqual(z.testzip(),None)
                    self.assertIn('SKILL.md',z.namelist())
                    self.assertFalse(any('__pycache__' in n for n in z.namelist()))
                    self.assertIn('scripts/rental_core.py',z.namelist())
                    if 'workbuddy' in path.name:
                        self.assertIn('description_zh:',z.read('SKILL.md').decode())
                        self.assertIn('author:',z.read('SKILL.md').decode())
    def test_install_refuses_overwrite(self):
        install=load('install')
        with tempfile.TemporaryDirectory() as tmp:
            dest=install.install(Path(tmp))
            self.assertTrue((dest/'SKILL.md').is_file())
            with self.assertRaises(FileExistsError): install.install(Path(tmp))
            self.assertTrue((dest/'SKILL.md').is_file())
    def test_install_avoids_recursive_source(self):
        install=load('install')
        with self.assertRaises(ValueError): install.install(ROOT/'skills/rental-finder-cn/nested')

if __name__=='__main__': unittest.main()
