"""Shared in-memory XLSX builders for upload tests."""
from io import BytesIO

import pytest
from openpyxl import Workbook


@pytest.fixture
def xlsx_bytes():
    def build(headers, rows):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(list(headers))
        for row in rows:
            worksheet.append(list(row))
        payload = BytesIO()
        workbook.save(payload)
        workbook.close()
        return payload.getvalue()

    return build
