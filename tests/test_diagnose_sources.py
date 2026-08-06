import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent


class DiagnoseSourcesImportTest(unittest.TestCase):
    def test_import_with_stringio_stdout_does_not_fail(self):
        module_name = "diagnose_sources_stringio_test"
        spec = importlib.util.spec_from_file_location(
            module_name, ROOT / "diagnose_sources.py"
        )
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, "stdout", io.StringIO()):
            spec.loader.exec_module(module)
        self.assertTrue(callable(module.configure_stdout))


if __name__ == "__main__":
    unittest.main()
