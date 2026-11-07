import json
import mimetypes
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
RECIPIENT = "Wilmervelazques12@gmail.com"
SERVICES = {
    "Interior painting",
    "Exterior painting",
    "Cabinet painting or refinishing",
    "Kitchen or bathroom remodeling",
    "Trim or carpentry",
    "Commercial painting or remodeling",
    "Other project",
}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MAX_REQUEST_SIZE = 10 * 1024


def send_lead_email(lead):
    host = os.environ.get("SMTP_HOST")
    username = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if not host or not username or not password:
        raise RuntimeError("SMTP settings are not configured.")

    message = EmailMessage()
    message["From"] = os.environ.get("SMTP_FROM", username)
    message["To"] = RECIPIENT
    message["Reply-To"] = lead["email"].strip()
    message["Subject"] = "Incoming Website Lead - WYV"
    message.set_content(
        "\n".join(
            [
                f"Name: {lead['name'].strip()}",
                f"Phone: {lead['phone'].strip()}",
                f"Email: {lead['email'].strip()}",
                f"Service: {lead['service']}",
                f"Project city or ZIP code: {lead.get('location', '').strip() or 'Not provided'}",
                "",
                "Project details:",
                lead["details"].strip(),
            ]
        )
    )

    port = int(os.environ.get("SMTP_PORT", "587"))
    if os.environ.get("SMTP_SECURE", "false").lower() == "true":
        with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as client:
            client.login(username, password)
            client.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as client:
            client.starttls(context=ssl.create_default_context())
            client.login(username, password)
            client.send_message(message)


def valid_lead(lead):
    if not isinstance(lead, dict):
        return False

    name = lead.get("name")
    phone = lead.get("phone")
    email = lead.get("email")
    service = lead.get("service")
    location = lead.get("location", "")
    details = lead.get("details")

    return (
        isinstance(name, str) and bool(name.strip()) and len(name) <= 120
        and isinstance(phone, str) and bool(phone.strip()) and len(phone) <= 40
        and isinstance(email, str) and len(email) <= 254 and EMAIL_PATTERN.fullmatch(email)
        and isinstance(service, str) and service in SERVICES
        and isinstance(location, str) and len(location) <= 120
        and isinstance(details, str) and bool(details.strip()) and len(details) <= 5000
    )


class WebsiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path in {"/", "/index.html"}:
            file_path = ROOT / "index.html"
        elif path in {"/styles.css", "/script.js"}:
            file_path = ROOT / path.lstrip("/")
        elif path.startswith("/assets/"):
            file_path = (ROOT / "assets" / path.removeprefix("/assets/")).resolve()
            if ROOT.joinpath("assets").resolve() not in file_path.parents:
                self.send_error(404)
                return
        else:
            self.send_error(404)
            return

        if not file_path.is_file():
            self.send_error(404)
            return

        content_type = (
            "text/html; charset=utf-8"
            if file_path.suffix == ".html"
            else mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        )
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def do_POST(self):
        if urlparse(self.path).path != "/api/lead":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json_response(400, {"error": "Please check the form and try again."})
            return

        if content_length <= 0 or content_length > MAX_REQUEST_SIZE:
            self._json_response(400, {"error": "Please check the form and try again."})
            return

        try:
            lead = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json_response(400, {"error": "Please check the form and try again."})
            return

        if not valid_lead(lead):
            self._json_response(400, {"error": "Please check the form and try again."})
            return

        try:
            send_lead_email(lead)
        except RuntimeError as error:
            print(f"Lead email is unavailable: {error}", flush=True)
            self._json_response(503, {"error": "Email service is not configured. Please call us instead."})
        except (OSError, smtplib.SMTPException, ValueError) as error:
            print(f"Failed to send website lead email: {error}", flush=True)
            self._json_response(502, {"error": "We couldn't send your request. Please try again or call us."})
        else:
            self._json_response(200, {"message": "Request sent."})

    def _json_response(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), WebsiteHandler)
    print(f"W.Y.V website server listening on port {port}", flush=True)
    server.serve_forever()
