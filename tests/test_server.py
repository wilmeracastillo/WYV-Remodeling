import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import server


VALID_LEAD = {
    "name": "Sample Client",
    "phone": "470-350-5727",
    "email": "client@example.com",
    "service": "Interior painting",
    "location": "Norcross, GA",
    "details": "Please provide an estimate for interior painting.",
}


class LeadEndpointTests(unittest.TestCase):
    def setUp(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.WebsiteHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.thread.join()
        self.httpd.server_close()

    def post_lead(self, lead):
        request = Request(
            f"{self.url}/api/lead",
            data=json.dumps(lead).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urlopen(request)
        except HTTPError as error:
            with error:
                return error.code, json.loads(error.read())
        with response:
            return response.status, json.loads(response.read())

    @patch("server.send_lead_email")
    def test_valid_submission_is_emailed(self, send_email):
        status, response = self.post_lead(VALID_LEAD)

        self.assertEqual(status, 200)
        self.assertEqual(response["message"], "Request sent.")
        send_email.assert_called_once_with(VALID_LEAD)

    @patch("server.send_lead_email")
    def test_invalid_submission_is_rejected(self, send_email):
        lead = {**VALID_LEAD, "service": ["unexpected"]}
        status, response = self.post_lead(lead)

        self.assertEqual(status, 400)
        self.assertIn("error", response)
        send_email.assert_not_called()

    def test_missing_smtp_configuration_returns_clear_error(self):
        with patch.dict(os.environ, {}, clear=True):
            status, response = self.post_lead(VALID_LEAD)

        self.assertEqual(status, 503)
        self.assertIn("not configured", response["error"])

    @patch("server.smtplib.SMTP")
    def test_email_has_requested_subject_and_all_form_values(self, smtp):
        smtp_client = smtp.return_value.__enter__.return_value
        environment = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_USER": "sender@example.com",
            "SMTP_PASSWORD": "test-password",
        }
        with patch.dict(os.environ, environment, clear=True):
            server.send_lead_email(VALID_LEAD)

        message = smtp_client.send_message.call_args.args[0]
        self.assertEqual(message["To"], "Wilmervelazques12@gmail.com")
        self.assertEqual(message["Subject"], "Incoming Website Lead - WYV")
        self.assertEqual(message["Reply-To"], VALID_LEAD["email"])
        body = message.get_content()
        for value in VALID_LEAD.values():
            self.assertIn(value, body)


if __name__ == "__main__":
    unittest.main()
