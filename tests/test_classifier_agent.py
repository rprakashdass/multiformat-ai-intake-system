import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from agents.classifier_agent import ClassifierAgent, Format, Intent

@pytest.fixture(scope="module")
def classifier_agent():
    return ClassifierAgent()

def test_email_rfq(classifier_agent):
    input_data = """
    Subject: Request for Quotation
    Please send us a quote for 5 high-performance servers and installation.
    """
    fmt, intent, _ = classifier_agent.classify_input(input_data)
    assert fmt == Format.EMAIL.value
    assert intent == Intent.RFQ.value

def test_json_invoice(classifier_agent):
    input_data = """
    {
        "invoice_id": "INV-001",
        "amount": 1200.00,
        "items": [{"description": "Consulting", "price": 1200.00}]
    }
    """
    fmt, intent, _ = classifier_agent.classify_input(input_data)
    assert fmt == Format.JSON.value
    assert intent == Intent.INVOICE.value

def test_pdf_regulation(classifier_agent):
    input_data = "Chapter 2: Data Use Policy — Companies must adhere to guidelines..."
    fmt, intent, _ = classifier_agent.classify_input(input_data)
    assert fmt == Format.PDF.value
    assert intent == Intent.REGULATION.value

def test_fraud_risk(classifier_agent):
    input_data = """
    {
        "transaction_id": "X123",
        "user_id": "abc",
        "amount": 99999,
        "country": "Nigeria",
        "device": "mobile"
    }
    """
    fmt, intent, _ = classifier_agent.classify_input(input_data)
    assert fmt == Format.JSON.value
    assert intent == Intent.FRAUD.value

def test_unclear(classifier_agent):
    input_data = "Hey just checking in on Tuesday’s meeting. Let me know."
    fmt, intent, _ = classifier_agent.classify_input(input_data)
    assert fmt == Format.EMAIL.value
    assert intent == Intent.OTHER.value
