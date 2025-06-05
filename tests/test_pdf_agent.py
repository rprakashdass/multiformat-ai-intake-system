import pytest
import json
import os
from unittest.mock import mock_open, patch
import pypdf

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.pdf_agent import PDFAgent


@pytest.fixture
def pdf_agent_instance(mocker):
    """Provides a PDFAgent instance with a mocked prompt file."""
    mock_prompt_content = """
    You are an advanced AI agent...
    Raw PDF Text Content to Process:
    ```
    {pdf_text_content}
    ```
    Extracted JSON Output:
    """
    mocker.patch('builtins.open', mock_open(read_data=mock_prompt_content))
    mocker.patch('os.path.exists', return_value=True)

    return PDFAgent()

def _mock_llm_response(mocker, mock_return_value):
    """Mocks the generate_output_from_prompt function and returns the mock object."""
    mock_obj = mocker.patch(
        'agents.pdf_agent.generate_output_from_prompt',
        return_value=mock_return_value
    )
    return mock_obj

#  Test Cases

def test_init_loads_prompt(mocker):
    """Verify PDFAgent initializes and loads the prompt template."""
    mock_prompt_content = "Test prompt content"
    mocker.patch('builtins.open', mock_open(read_data=mock_prompt_content))
    mocker.patch('os.path.exists', return_value=True)

    agent = PDFAgent()
    assert agent.prompt_template == mock_prompt_content

def test_init_handles_missing_prompt_file(mocker):
    """Verify PDFAgent raises FileNotFoundError if prompt file is missing."""
    mocker.patch('builtins.open', side_effect=FileNotFoundError("Prompt not found"))
    mocker.patch('os.path.exists', return_value=False)

    with pytest.raises(FileNotFoundError, match="Prompt not found"):
        PDFAgent()

def test_extract_text_from_pdf_success(pdf_agent_instance, mocker):
    """Tests successful text extraction from a mocked PDF file."""
    mock_pdf_content = "This is a test PDF content."
    mocker.patch('builtins.open', mock_open(read_data=b"dummy pdf bytes"))
    mocker.patch('pypdf.PdfReader').return_value.pages = [
        mocker.Mock(extract_text=lambda: mock_pdf_content)
    ]
    mocker.patch('os.path.exists', return_value=True)

    text = pdf_agent_instance._extract_text_from_pdf("dummy.pdf")
    assert text.strip() == mock_pdf_content.strip()

def test_extract_text_from_pdf_file_not_found(pdf_agent_instance, mocker):
    """Tests _extract_text_from_pdf when the file does not exist."""
    mocker.patch('os.path.exists', return_value=False)

    with pytest.raises(FileNotFoundError, match="PDF file not found"):
        pdf_agent_instance._extract_text_from_pdf("non_existent.pdf")

def test_extract_text_from_pdf_corrupted_file(pdf_agent_instance, mocker):
    """Tests _extract_text_from_pdf with a corrupted/unreadable PDF."""
    mocker.patch('builtins.open', mock_open(read_data=b"corrupted bytes"))
    mocker.patch('pypdf.PdfReader', side_effect=pypdf.errors.PdfReadError("Bad PDF"))
    mocker.patch('os.path.exists', return_value=True)

    with pytest.raises(ValueError, match="Could not read PDF file"):
        pdf_agent_instance._extract_text_from_pdf("corrupted.pdf")

def test_process_pdf_text_content_success(pdf_agent_instance, mocker):
    """Tests successful processing of PDF text content by LLM."""
    mock_text = "Invoice INV-2024-001 for $100.00."
    expected_llm_output = json.dumps({
        "document_id": "INV-2024-001",
        "document_type": "invoice",
        "summary": "Invoice for $100.00.",
        "total_amount": 100.00,
        "potential_action_type": "Log Transaction"
    })
    mock_llm_helper = _mock_llm_response(mocker, expected_llm_output)

    result = pdf_agent_instance.process_pdf_text_content(mock_text)

    assert result["document_id"] == "INV-2024-001"
    assert result["total_amount"] == 100.00
    assert result["potential_action_type"] == "Log Transaction"
    mock_llm_helper.assert_called_once()
    mock_llm_helper.assert_called_once_with(
        mocker.ANY,
        model_name=pdf_agent_instance.model_name,
        temperature=0.2
    )

def test_process_pdf_text_content_empty_input(pdf_agent_instance, mocker):
    """Tests handling of empty text content passed to process_pdf_text_content."""
    mock_llm_helper = mocker.patch('agents.pdf_agent.generate_output_from_prompt')

    result = pdf_agent_instance.process_pdf_text_content("")

    assert "error" in result
    assert "Empty or unreadable PDF content" in result["error"]
    assert result["potential_action_type"] == "Flag Unreadable Document"
    mock_llm_helper.assert_not_called()

def test_process_pdf_text_content_llm_malformed_json(pdf_agent_instance, mocker):
    """Tests handling when the LLM returns malformed JSON."""
    mock_text = "Some valid text for LLM."
    malformed_llm_output = "This is not valid JSON"
    mock_llm_helper = _mock_llm_response(mocker, malformed_llm_output)

    result = pdf_agent_instance.process_pdf_text_content(mock_text)

    assert "error" in result
    assert "Malformed JSON from LLM" in result["error"]
    assert result["potential_action_type"] == "Flag LLM Output Error"
    assert result["raw_llm_response"] == malformed_llm_output
    mock_llm_helper.assert_called_once()

def test_process_pdf_text_content_llm_unexpected_error(pdf_agent_instance, mocker):
    """Tests handling an unexpected error during LLM response processing (e.g., KeyError if LLM output is valid but unexpected)."""
    mock_text = "Text for an unexpected error."

    valid_but_unexpected_llm_output = json.dumps({"unexpected_key": "value"})
    mock_llm_helper = _mock_llm_response(mocker, valid_but_unexpected_llm_output)

    result = pdf_agent_instance.process_pdf_text_content(mock_text)

    assert "error" in result
    assert "Unexpected error" in result["error"]
    assert result["potential_action_type"] == "Flag Processing Error"
    mock_llm_helper.assert_called_once()


def test_process_pdf_text_content_compliance_flags(pdf_agent_instance, mocker):
    """Tests extraction and flagging for regulatory compliance keywords."""
    mock_text = "This document contains information related to GDPR and sensitive HIPAA data."
    expected_llm_output = json.dumps({
        "document_type": "policy",
        "document_id": "generated-id-123",
        "summary": "Document discussing GDPR and HIPAA compliance.",
        "sender_or_issuer_info": None,
        "date": None,
        "total_amount": None,
        "currency": None,
        "line_items": [],
        "mentions_regulatory_keywords": True,
        "identified_regulatory_keywords": ["GDPR", "HIPAA"],
        "is_high_value_invoice": False,
        "missing_fields": [],
        "anomalies": [],
        "potential_action_type": "Flag Compliance Document"
    })
    mock_llm_helper = _mock_llm_response(mocker, expected_llm_output)

    result = pdf_agent_instance.process_pdf_text_content(mock_text)

    assert result["document_type"] == "policy"
    assert result["mentions_regulatory_keywords"] is True
    assert "GDPR" in result["identified_regulatory_keywords"]
    assert result["potential_action_type"] == "Flag Compliance Document"
