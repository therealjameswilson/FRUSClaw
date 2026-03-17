"""WhatsApp Cloud API scaffold for FRUSClaw."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib import error, request

from frusclaw_agent.actions import FrusResearchService, FrusSkillProvider
from frusclaw_agent.channels.base import BaseChannelAdapter, ChannelEnvelope, ChannelResult
from frusclaw_agent.config import load_agent_settings
from frusclaw_agent.models import AgentSettings
from frusclaw_agent.providers import ChannelMessage


DENIAL_MESSAGE = "Access denied. This FRUSClaw instance only accepts approved users."
LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class WhatsAppAdapterStatus:
    """Validation summary for the WhatsApp scaffold."""

    valid: bool
    errors: list[str]
    allowed_user_count: int
    webhook_url: str
    api_version: str


@dataclass(slots=True)
class WhatsAppIncomingMessage:
    """Normalized inbound WhatsApp text message."""

    from_user: str
    text: str
    message_id: str


class WhatsAppChannelAdapter(BaseChannelAdapter):
    """Config-validating WhatsApp Cloud API scaffold."""

    def __init__(
        self,
        settings: AgentSettings,
        service: FrusResearchService,
        urlopen: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings
        self.service = service
        self.skill = FrusSkillProvider(service)
        self.urlopen = urlopen or request.urlopen

    @classmethod
    def from_config_path(
        cls,
        config_path: Path,
        service: FrusResearchService,
        urlopen: Callable[..., Any] | None = None,
    ) -> "WhatsAppChannelAdapter":
        """Build an adapter from the local FRUSClaw config path."""
        return cls(load_agent_settings(config_path), service, urlopen=urlopen)

    def validate_config(self) -> list[str]:
        """Return WhatsApp scaffold config errors."""
        errors: list[str] = []
        if not self.settings.whatsapp_access_token.strip():
            errors.append("missing WHATSAPP_ACCESS_TOKEN")
        if not self.settings.whatsapp_phone_number_id.strip():
            errors.append("missing WHATSAPP_PHONE_NUMBER_ID")
        if not self.settings.whatsapp_verify_token.strip():
            errors.append("missing WHATSAPP_VERIFY_TOKEN")
        if not self.settings.allowed_users:
            errors.append("missing FRUSCLAW_ALLOWED_USERS")
        if self.settings.whatsapp_webhook_port <= 0:
            errors.append("WHATSAPP_WEBHOOK_PORT must be greater than 0")
        return errors

    def status(self) -> WhatsAppAdapterStatus:
        """Return a summary of current adapter readiness."""
        errors = self.validate_config()
        return WhatsAppAdapterStatus(
            valid=not errors,
            errors=errors,
            allowed_user_count=len(self.settings.allowed_users),
            webhook_url=f"http://{self.settings.whatsapp_webhook_host}:{self.settings.whatsapp_webhook_port}",
            api_version=self.settings.whatsapp_api_version,
        )

    def is_allowed_user(self, user_id: str) -> bool:
        """Return whether a WhatsApp sender is allowlisted."""
        return user_id in self.settings.allowed_users

    def handle_message(self, envelope: ChannelEnvelope) -> ChannelResult:
        """Route one WhatsApp-style message through existing FRUS actions."""
        if not self.is_allowed_user(envelope.user_id):
            return ChannelResult(ok=False, text=DENIAL_MESSAGE)

        response = self.skill.handle(
            ChannelMessage(
                channel="whatsapp",
                user_id=envelope.user_id,
                text=envelope.text,
                mode=envelope.mode,
            )
        )
        return ChannelResult(ok=True, text=response)

    def verify_webhook(
        self,
        mode: str | None,
        token: str | None,
        challenge: str | None,
    ) -> tuple[int, str]:
        """Handle Meta webhook verification handshake."""
        if mode != "subscribe" or token != self.settings.whatsapp_verify_token:
            return 403, "forbidden"
        return 200, challenge or ""

    def verify_signature(self, body: bytes, signature_header: str | None) -> bool:
        """Optionally verify the webhook signature if an app secret is configured."""
        if not self.settings.whatsapp_app_secret:
            return True
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(
            self.settings.whatsapp_app_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        provided = signature_header.removeprefix("sha256=")
        return hmac.compare_digest(expected, provided)

    def parse_incoming_messages(self, payload: dict[str, Any]) -> list[WhatsAppIncomingMessage]:
        """Extract inbound text messages from a WhatsApp webhook payload."""
        messages: list[WhatsAppIncomingMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    if message.get("type") != "text":
                        continue
                    text_body = message.get("text", {}).get("body", "")
                    from_user = message.get("from", "")
                    message_id = message.get("id", "")
                    if not from_user or not text_body:
                        continue
                    messages.append(
                        WhatsAppIncomingMessage(
                            from_user=from_user,
                            text=text_body,
                            message_id=message_id,
                        )
                    )
        return messages

    def outbound_payload(self, to_phone: str, text: str) -> dict[str, Any]:
        """Build a WhatsApp Cloud API text payload."""
        return {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

    def send_text(self, to_phone: str, text: str) -> tuple[bool, str]:
        """Send a text reply using the WhatsApp Cloud API."""
        payload = self.outbound_payload(to_phone, text)
        api_url = (
            f"https://graph.facebook.com/{self.settings.whatsapp_api_version}/"
            f"{self.settings.whatsapp_phone_number_id}/messages"
        )
        body = json.dumps(payload).encode("utf-8")
        request_obj = request.Request(
            api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self.urlopen(request_obj, timeout=15) as response:
                response_body = response.read().decode("utf-8")
            return True, response_body
        except error.HTTPError as exc:
            failure_body = exc.read().decode("utf-8", errors="replace")
            LOGGER.error("whatsapp send failed: %s", failure_body)
            return False, failure_body
        except error.URLError as exc:
            LOGGER.error("whatsapp send failed: %s", exc)
            return False, str(exc)

    def process_webhook_payload(self, payload: dict[str, Any]) -> list[ChannelResult]:
        """Route parsed incoming WhatsApp messages into FRUS actions."""
        results: list[ChannelResult] = []
        for message in self.parse_incoming_messages(payload):
            results.append(
                self.handle_message(
                    ChannelEnvelope(user_id=message.from_user, text=message.text, mode=self.settings.mode)
                )
            )
        return results

    def run_webhook_server(self) -> str:
        """Start a simple local webhook server."""
        errors = self.validate_config()
        if errors:
            raise RuntimeError("; ".join(errors))

        server = ThreadingHTTPServer(
            (self.settings.whatsapp_webhook_host, self.settings.whatsapp_webhook_port),
            self._handler_class(),
        )
        server.adapter = self  # type: ignore[attr-defined]
        try:
            server.serve_forever()
        finally:
            server.server_close()
        return "webhook stopped"

    def run(self) -> str:
        """Return scaffold readiness for WhatsApp."""
        errors = self.validate_config()
        if errors:
            raise RuntimeError("; ".join(errors))
        return (
            "whatsapp: scaffold ready "
            f"(api_version={self.settings.whatsapp_api_version}, "
            f"allowed_users={len(self.settings.allowed_users)})"
        )

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        adapter = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                mode = self._query_param("hub.mode")
                token = self._query_param("hub.verify_token")
                challenge = self._query_param("hub.challenge")
                status_code, body = adapter.verify_webhook(mode=mode, token=token, challenge=challenge)
                self._send_text(status_code, body)

            def do_POST(self) -> None:  # noqa: N802
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length)
                signature = self.headers.get("X-Hub-Signature-256")
                if not adapter.verify_signature(body, signature):
                    self._send_json(403, {"status": "forbidden"})
                    return
                payload = json.loads(body.decode("utf-8") or "{}")
                results = adapter.process_webhook_payload(payload)
                for message, result in zip(adapter.parse_incoming_messages(payload), results):
                    ok, _ = adapter.send_text(message.from_user, result.text)
                    if not ok:
                        LOGGER.error("failed to send whatsapp reply to %s", message.from_user)
                self._send_json(200, {"status": "ok", "messages": len(results)})

            def log_message(self, format: str, *args: object) -> None:
                return None

            def _query_param(self, key: str) -> str | None:
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(self.path)
                values = parse_qs(parsed.query).get(key)
                return values[0] if values else None

            def _send_text(self, status_code: int, body: str) -> None:
                encoded = body.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return Handler
