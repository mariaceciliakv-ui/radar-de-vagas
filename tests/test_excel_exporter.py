"""Testes unitários para validação de concorrência e resiliência do ExcelExporter."""

import os
import unittest
from unittest.mock import patch
import openpyxl

from src.exporters.excel_exporter import ExcelExporter


class TestExcelExporterConcurrency(unittest.TestCase):

    def setUp(self):
        self.test_dir = "tests/temp_test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_dir, "test_radar.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "🎯 Vagas Recomendadas"
        ws.cell(1, 1, "Teste")
        wb.save(self.test_file)
        wb.close()

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_safe_load_workbook_normal(self):
        wb = ExcelExporter._safe_load_workbook(self.test_file)
        self.assertIn("🎯 Vagas Recomendadas", wb.sheetnames)
        wb.close()

    def test_safe_load_workbook_fallback_on_permission_error(self):
        original_load = openpyxl.load_workbook

        def mock_load(filename, *args, **kwargs):
            # Se tentar abrir o arquivo original diretamente, simula erro de lock do Excel
            if os.path.abspath(filename) == os.path.abspath(self.test_file):
                raise PermissionError("[Errno 13] Permission denied (Excel lock)")
            return original_load(filename, *args, **kwargs)

        with patch("openpyxl.load_workbook", side_effect=mock_load):
            wb = ExcelExporter._safe_load_workbook(self.test_file)
            self.assertIn("🎯 Vagas Recomendadas", wb.sheetnames)
            wb.close()

    def test_safe_save_workbook_normal(self):
        wb = openpyxl.Workbook()
        saved_path = ExcelExporter._safe_save_workbook(wb, self.test_file)
        self.assertEqual(saved_path, self.test_file)
        wb.close()

    def test_safe_save_workbook_fallback_on_permission_error(self):
        wb = openpyxl.Workbook()
        original_save = wb.save

        def mock_save(filename):
            if os.path.abspath(filename) == os.path.abspath(self.test_file):
                raise PermissionError("[Errno 13] Permission denied (Excel lock)")
            return original_save(filename)

        with patch.object(wb, "save", side_effect=mock_save):
            saved_path = ExcelExporter._safe_save_workbook(wb, self.test_file)
            expected_fallback = self.test_file.replace(".xlsx", "_atualizada.xlsx")
            self.assertEqual(saved_path, expected_fallback)
            self.assertTrue(os.path.exists(expected_fallback))
        wb.close()


if __name__ == "__main__":
    unittest.main()
