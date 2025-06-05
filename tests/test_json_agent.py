import pytest
import json
from unittest.mock import mock_open

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.json_agent import JSONAgent


@pytest.fixture
def json_agent_instance(mocker):
    """Provides a JSONAgent instance with a mocked prompt file for consistent testing."""
    mock_prompt_content = """
    You are an expert data extraction and reformatting agent for FlowBit AI.
    Your task is to take an arbitrary JSON object and extract relevant information,
    transforming it into our standardized FlowBit schema. You must also identify
    any missing required fields or data anomalies.

    Here is the target FlowBit schema:
    ```json
    {flowbit_schema_json}
    ```

    Required FlowBit fields that must be present or inferrable:
    {required_flowbit_fields_json}

    Important instructions:
    1. Map the data from the 'arbitrary_json_input' into the fields of the 'FlowBit schema'.
    2. For `document_id`, try to find a unique identifier. If not found, use a placeholder.
    3. For `document_type`, classify the overall type.
    4. For `sender_info`, extract name, email, organization.
    5. For `date`, convert to 'YYYY-MM-DD' format.
    6. For `summary`, provide a concise summary.
    7. For `key_values`, extract 3-5 important high-level pairs.
    8. For `line_items`, extract detailed item information. Calculate 'total' if missing.
    9. For `total_amount` and `currency`, extract if applicable.
    10. For `required_fields_status`, indicate true/false for each required field.
    11. In `missing_fields`, list fields from required_flowbit_fields not found.
    12. In `anomalies`, describe unusual/incorrect data points.
    13. Your response MUST be a JSON object, strictly conforming to the structure of the FlowBit schema.
    14. Include a `potential_action_type` field: "Log Transaction", "Flag for Review", "Escalate Fraud Alert".

    Arbitrary JSON Input to Process:
    ```json
    {arbitrary_input_json}
    ```
    JSON Output (following FlowBit Schema):
    """
    mocker.patch('builtins.open', mock_open(read_data=mock_prompt_content))
    mocker.patch('os.path.exists', return_value=True)

    return JSONAgent()


def _mock_llm_response(mocker, mock_return_value):
    """Mocks the generate_output_from_prompt function and returns the mock object."""
    mock_object = mocker.patch(
        'agents.json_agent.generate_output_from_prompt',
        return_value=mock_return_value
    )
    return mock_object


def test_extract_and_format_clean_order(json_agent_instance, mocker):
    """Tests a clean order webhook payload extraction."""
    raw_json_input = """
    {
      "event": "order_created",
      "data": {
        "id": "WEB-ORD-001",
        "customer": {
          "first_name": "Alice",
          "last_name": "Smith",
          "email": "alice.smith@example.com"
        },
        "order_details": {
          "date_placed": "2024-05-27T10:30:00Z",
          "items": [
            {"product_code": "P101", "name": "Wireless Mouse", "qty": 2, "price": 25.50},
            {"product_code": "K202", "name": "Mechanical Keyboard", "qty": 1, "price": 80.00}
          ],
          "total": 131.00,
          "currency_code": "USD"
        }
      }
    }
    """
    expected_llm_output = json.dumps({
        "document_id": "WEB-ORD-001",
        "document_type": "order",
        "sender_info": {"name": "Alice Smith", "email": "alice.smith@example.com", "organization": None},
        "date": "2024-05-27",
        "summary": "Order created for Alice Smith with two items, total $131.00 USD.",
        "key_values": {"event": "order_created", "total": 131.00},
        "line_items": [
            {"description": "Wireless Mouse", "quantity": 2, "unit_price": 25.50, "total": 51.00},
            {"description": "Mechanical Keyboard", "quantity": 1, "unit_price": 80.00, "total": 80.00}
        ],
        "total_amount": 131.00,
        "currency": "USD",
        "required_fields_status": {"document_id": True, "document_type": True, "summary": True},
        "missing_fields": [],
        "anomalies": [],
        "potential_action_type": "Log Transaction"
    })

    mock_llm_helper = _mock_llm_response(mocker, expected_llm_output)
    result = json_agent_instance.extract_and_format(raw_json_input)

    assert result["document_id"] == "WEB-ORD-001"
    assert result["document_type"] == "order"
    assert result["total_amount"] == 131.00
    assert result["potential_action_type"] == "Log Transaction"
    assert len(result["anomalies"]) == 0
    assert len(result["missing_fields"]) == 0
    mock_llm_helper.assert_called_once()
    mock_llm_helper.assert_called_once_with(
        mocker.ANY,
        model_name=json_agent_instance.model_name,
        temperature=0.2
    )


def test_extract_and_format_product_anomaly(json_agent_instance, mocker):
    """Tests input with a negative price (anomaly)."""
    raw_json_input = """
    {
      "product_id": "PROD-XYZ",
      "product_name": "Super Gadget",
      "price": -100.00,
      "stock_count": 500
    }
    """
    expected_llm_output = json.dumps({
        "document_id": "PROD-XYZ",
        "document_type": "product_info",
        "sender_info": None,
        "date": None,
        "summary": "Information about a product called Super Gadget with a negative price.",
        "key_values": {"product_name": "Super Gadget", "price": -100.00},
        "line_items": [],
        "total_amount": None,
        "currency": None,
        "required_fields_status": {"document_id": True, "document_type": True, "summary": True},
        "missing_fields": [],
        "anomalies": ["Price is negative (-100.00), which is unusual for a product price."],
        "potential_action_type": "Flag for Review"
    })

    mock_llm_helper = _mock_llm_response(mocker, expected_llm_output)
    result = json_agent_instance.extract_and_format(raw_json_input)

    assert result["document_id"] == "PROD-XYZ"
    assert result["potential_action_type"] == "Flag for Review"
    assert "Price is negative" in result["anomalies"][0]
    assert len(result["missing_fields"]) == 0
    mock_llm_helper.assert_called_once()
    mock_llm_helper.assert_called_once_with(
        mocker.ANY,
        model_name=json_agent_instance.model_name,
        temperature=0.2
    )


def test_extract_and_format_missing_required_fields(json_agent_instance, mocker):
    """Tests input where a required field (document_id) is missing."""
    raw_json_input = """
    {
      "report_title": "Daily Summary",
      "generation_date": "2024-05-30",
      "generator": "System A"
    }
    """
    expected_llm_output = json.dumps({
        "document_id": "GENERATED_ID_XYZ-20240530",
        "document_type": "report",
        "sender_info": {"name": "System A", "email": None, "organization": None},
        "date": "2024-05-30",
        "summary": "Daily Summary report generated by System A.",
        "key_values": {"report_title": "Daily Summary"},
        "line_items": [],
        "total_amount": None,
        "currency": None,
        "required_fields_status": {"document_id": False, "document_type": True, "summary": True},
        "missing_fields": ["document_id"],
        "anomalies": [],
        "potential_action_type": "Flag for Review"
    })

    mock_llm_helper = _mock_llm_response(mocker, expected_llm_output)
    result = json_agent_instance.extract_and_format(raw_json_input)

    assert result["document_type"] == "report"
    assert "document_id" in result["missing_fields"]
    assert result["potential_action_type"] == "Flag for Review"
    mock_llm_helper.assert_called_once()
    mock_llm_helper.assert_called_once_with(
        mocker.ANY,
        model_name=json_agent_instance.model_name,
        temperature=0.2
    )


def test_extract_and_format_malformed_input_json(json_agent_instance, mocker):
    """Tests the agent's internal handling of invalid input JSON."""
    raw_json_input = """
    {
      "name": "Invalid JSON",
      "value": 123
      "status": "error" // Missing comma here
    }
    """
    mock_llm_helper = mocker.patch('agents.json_agent.generate_output_from_prompt')

    result = json_agent_instance.extract_and_format(raw_json_input)

    assert "error" in result
    assert "Invalid JSON input" in result["error"]
    assert result["potential_action_type"] == "Flag Invalid Input"
    mock_llm_helper.assert_not_called()


def test_extract_and_format_empty_input_string(json_agent_instance, mocker):
    """Tests handling of an empty input string."""
    mock_llm_helper = mocker.patch('agents.json_agent.generate_output_from_prompt')

    result = json_agent_instance.extract_and_format("")

    assert "error" in result
    assert "Empty JSON input provided" in result["error"]
    assert result["potential_action_type"] == "Flag Invalid Input"
    mock_llm_helper.assert_not_called()


def test_extract_and_format_llm_returns_malformed_json(json_agent_instance, mocker):
    """Tests handling if the LLM returns malformed JSON."""
    raw_json_input = '{"valid": "json"}'
    mock_llm_helper = _mock_llm_response(mocker, "This is not valid JSON from LLM")

    result = json_agent_instance.extract_and_format(raw_json_input)

    assert "error" in result
    assert "Malformed JSON from LLM" in result["error"]
    assert "raw_llm_response" in result
    assert result["potential_action_type"] == "Flag LLM Output Error"
    mock_llm_helper.assert_called_once()
    mock_llm_helper.assert_called_once_with(
        mocker.ANY,
        model_name=json_agent_instance.model_name,
        temperature=0.2
    )


def test_extract_and_format_llm_returns_valid_but_incomplete_json(json_agent_instance, mocker):
    """Tests if LLM returns valid JSON but misses some expected keys."""
    raw_json_input = '{"some": "data"}'
    expected_llm_output = json.dumps({"status": "partial_success", "extra_info": "foo"})

    mock_llm_helper = _mock_llm_response(mocker, expected_llm_output)
    result = json_agent_instance.extract_and_format(raw_json_input)

    assert "status" in result
    assert result.get("status") == "partial_success"
    mock_llm_helper.assert_called_once()
    mock_llm_helper.assert_called_once_with(
        mocker.ANY,
        model_name=json_agent_instance.model_name,
        temperature=0.2
    )