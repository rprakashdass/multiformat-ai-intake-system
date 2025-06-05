import unittest
from unittest.mock import patch

import os
import sys
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.email_agent import EmailAgent

class TestEmailAgentClassifier(unittest.TestCase):
    def setUp(self):
        self.agent = EmailAgent()

    @patch('agents.email_agent.generate_output_from_prompt')
    def test_high_urgency_escalation_email(self, mock_llm):
        # Mock LLM output for a high urgency escalation email
        llm_response = json.dumps({
            "sender_name": "Frustrated Client",
            "sender_email": "customer_support@example.com",
            "subject": "EXTREMELY URGENT: Major System Failure",
            "issue_summary": "Production system down, costing thousands per minute.",
            "urgency": "High",
            "tone": "Escalation",
            "potential_action_type": "Immediate Attention"
        })
        mock_llm.return_value = llm_response

        email_content = """
        From: customer_support@example.com
        Subject: EXTREMELY URGENT: Major System Failure on Account #CUST123

        Our primary production system is completely down due to your recent update.
        This is costing us thousands of dollars per minute. Immediate attention needed.
        """

        result = self.agent.process_email(email_content)

        self.assertEqual(result["urgency"], "High")
        self.assertEqual(result["tone"], "Escalation")
        self.assertEqual(result["sender_name"], "Frustrated Client")
        self.assertEqual(result["potential_action_type"], "Immediate Attention")

    @patch('agents.email_agent.generate_output_from_prompt')
    def test_routine_question_email(self, mock_llm):
        # Mock LLM output for a routine question with neutral tone and medium urgency
        llm_response = json.dumps({
            "sender_name": "Curious Learner",
            "sender_email": "inquiries@flowbit.com",
            "subject": "Follow-up on recent webinar",
            "issue_summary": "Question about data integration features and API availability.",
            "urgency": "Medium",
            "tone": "Question",
            "potential_action_type": "Provide Information"
        })
        mock_llm.return_value = llm_response

        email_content = """
        From: inquiries@flowbit.com
        Subject: Follow-up on recent webinar

        I had a quick question about the data integration features. Is there a simple API for pushing custom data?
        """

        result = self.agent.process_email(email_content)

        self.assertEqual(result["urgency"], "Medium")
        self.assertEqual(result["tone"], "Question")
        self.assertEqual(result["sender_name"], "Curious Learner")
        self.assertEqual(result["potential_action_type"], "Provide Information")

    @patch('agents.email_agent.generate_output_from_prompt')
    def test_informative_update_email(self, mock_llm):
        # Mock LLM output for an informative update with low urgency and informative tone
        llm_response = json.dumps({
            "sender_name": "DevOps Team",
            "sender_email": "devops@yourcompany.com",
            "subject": "Scheduled Maintenance Notification",
            "issue_summary": "Scheduled maintenance on database servers this Saturday.",
            "urgency": "Low",
            "tone": "Informative",
            "potential_action_type": "Notification"
        })
        mock_llm.return_value = llm_response

        email_content = """
        From: devops@yourcompany.com
        Subject: Scheduled Maintenance Notification

        Scheduled maintenance on our database servers this Saturday from 2 AM to 4 AM UTC.
        """

        result = self.agent.process_email(email_content)

        self.assertEqual(result["urgency"], "Low")
        self.assertEqual(result["tone"], "Informative")
        self.assertEqual(result["sender_name"], "DevOps Team")
        self.assertEqual(result["potential_action_type"], "Notification")

    @patch('agents.email_agent.generate_output_from_prompt')
    def test_threatening_email(self, mock_llm):
        # Mock LLM output for a threatening email
        llm_response = json.dumps({
            "sender_name": "Unknown Sender",
            "sender_email": "unknown_sender@darkweb.com",
            "subject": "Your system's security is compromised",
            "issue_summary": "Unauthorized access detected. Expect consequences.",
            "urgency": "High",
            "tone": "Threatening",
            "potential_action_type": "Security Alert"
        })
        mock_llm.return_value = llm_response

        email_content = """
        From: unknown_sender@darkweb.com
        Subject: Your system's security is compromised

        We have gained access to your internal network. Expect consequences if demands are not met.
        """

        result = self.agent.process_email(email_content)

        self.assertEqual(result["urgency"], "High")
        self.assertEqual(result["tone"], "Threatening")
        self.assertEqual(result["sender_name"], "Unknown Sender")
        self.assertEqual(result["potential_action_type"], "Security Alert")

if __name__ == "__main__":
    unittest.main()