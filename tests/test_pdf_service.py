import pytest
from io import BytesIO
from unittest.mock import MagicMock
from app.services.pdf_service import generate_invoice_pdf
from app.models.models import Invoice, Client, InvoiceLine
import datetime

def test_generate_invoice_pdf_success():
    # Setup mock client
    mock_client = Client(
        name="Test Client",
        address="123 Test St, Paris",
        vat_number="FR123456789",
        siren="123456789"
    )
    
    # Setup mock invoice
    mock_invoice = Invoice(
        invoice_number="INV-2023-001",
        issue_date=datetime.datetime.now(),
        due_date=datetime.datetime.now() + datetime.timedelta(days=30),
        client=mock_client,
        total_ht=100.0,
        total_tva=20.0,
        total_ttc=120.0
    )
    
    # Setup mock lines
    line1 = InvoiceLine(
        description="Service A",
        quantity=1,
        unit_price_ht=80.0,
        tva_rate=20.0,
        total_ht=80.0
    )
    line2 = InvoiceLine(
        description="Service B",
        quantity=2,
        unit_price_ht=10.0,
        tva_rate=20.0,
        total_ht=20.0
    )
    mock_invoice.lines = [line1, line2]
    
    # Generate PDF
    pdf_buffer = generate_invoice_pdf(mock_invoice)
    
    assert isinstance(pdf_buffer, BytesIO)
    assert pdf_buffer.getbuffer().nbytes > 0
    
    # Reset buffer and check if it's a valid PDF (starts with %PDF)
    pdf_buffer.seek(0)
    header = pdf_buffer.read(4)
    assert header == b'%PDF'

def test_generate_invoice_pdf_minimal_data():
    # Setup mock client with minimal data
    mock_client = Client(
        name="Minimal Client"
    )
    
    # Setup mock invoice
    mock_invoice = Invoice(
        invoice_number="INV-MIN",
        client=mock_client,
        total_ht=0,
        total_tva=0,
        total_ttc=0
    )
    mock_invoice.lines = []
    
    # Generate PDF
    pdf_buffer = generate_invoice_pdf(mock_invoice)
    
    assert isinstance(pdf_buffer, BytesIO)
    assert pdf_buffer.getbuffer().nbytes > 0
    
    pdf_buffer.seek(0)
    assert pdf_buffer.read(4) == b'%PDF'
