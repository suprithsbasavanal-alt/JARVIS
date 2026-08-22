# JARVIS Integrations Framework & Contract Specifications

> **Phase 0 — Safe Development Specification**

This document specifies the abstract integration contracts, security scoping, rate-limiting, and confirmation requirements for external services planned in future phases.

---

## 1. Integration Strategy & Safety Posture

1. **Phase 0 Constraint**: No real external API keys, tokens, or network sockets are connected during Phase 0.
2. **Interface First**: All integrations inherit from `BaseIntegration` with strict typing and simulated sandbox implementations (`sandbox/mock_services.py`).
3. **Read-Only by Default**: Reading emails, messages, and calendars is granted under `NORMAL` tier.
4. **Mandatory Confirmation for Outbound Operations**: Sending emails, dispatching chat messages, editing events, or posting to social media is classified as `SENSITIVE` and strictly gated behind human confirmation.

---

## 2. Integration Matrix

| Integration | Service Category | Planned Protocol / Library | Default Scope | Outbound Gate |
|---|---|---|---|---|
| **Gmail** | Email | Google Workspace REST API / OAuth 2.0 PKCE | `gmail.readonly` | SENSITIVE (Dry-run preview) |
| **Google Calendar** | Calendar | Google Calendar v3 REST API | `calendar.events.readonly` | SENSITIVE (Event diff) |
| **Apple Calendar** | Calendar | macOS EventKit (Swift / Objective-C Bridge) | Native EventKit Read | SENSITIVE (Event diff) |
| **WhatsApp** | Messaging | WhatsApp Business Cloud API / Local Web Bridge | Scoped Session Read | SENSITIVE (Full message text) |
| **Telegram** | Messaging | Telegram Bot API / TDLib Client | Scoped Chat Read | SENSITIVE (Full message text) |
| **SMS** | Messaging | Android Telephony Bridge / Apple Messages Script | Scoped Message Read | SENSITIVE (Full message text) |
| **Instagram** | Social Media | Instagram Graph API | Read profile / analytics | SENSITIVE (Media + caption) |
| **Browser** | Web Research | Playwright / Chromium Sandbox (Headless) | Local sandbox browsing | NORMAL for search; SENSITIVE for logins |
| **Mac Applications** | Desktop | AppleScript / Accessibility API Bridge | Scoped App automation | SENSITIVE (Action preview) |
| **Android APIs** | Mobile | Android Intent / NotificationListenerService | Notification read | SENSITIVE (Intent preview) |

---

## 3. Abstract Contract Definitions

### 3.1. Email Integration Contract (`EmailServiceContract`)
```python
class EmailDraft(BaseModel):
    recipient: str
    subject: str
    body_text: str
    attachments: list[str] = []

class EmailContract(ABC):
    @abstractmethod
    async def list_unread_messages(self, limit: int = 10) -> list[dict]: ...

    @abstractmethod
    async def get_message(self, message_id: str) -> dict: ...

    @abstractmethod
    async def prepare_draft(self, draft: EmailDraft) -> str: ...

    @abstractmethod
    async def send_email(self, draft_id: str, approval_token: str) -> bool: ...
```

### 3.2. Calendar Integration Contract (`CalendarServiceContract`)
```python
class CalendarEvent(BaseModel):
    title: str
    start_time: str
    end_time: str
    attendees: list[str] = []
    location: str | None = None

class CalendarContract(ABC):
    @abstractmethod
    async def list_upcoming_events(self, days: int = 7) -> list[CalendarEvent]: ...

    @abstractmethod
    async def create_event(self, event: CalendarEvent, approval_token: str) -> str: ...

    @abstractmethod
    async def delete_event(self, event_id: str, approval_token: str) -> bool: ...
```

### 3.3. Messaging Integration Contract (`MessagingServiceContract`)
```python
class OutboundMessage(BaseModel):
    recipient_id: str
    platform: Literal["whatsapp", "telegram", "sms"]
    text_content: str

class MessagingContract(ABC):
    @abstractmethod
    async def list_recent_chats(self, platform: str) -> list[dict]: ...

    @abstractmethod
    async def send_message(self, message: OutboundMessage, approval_token: str) -> bool: ...
```

---

## 4. Sandboxed Mock Verification

In Phase 0 through Phase 8, all integration tests and agent workflows interact strictly with the mock implementations provided in `sandbox/mock_services.py` backed by static JSON fixtures in `sandbox/fixtures/`:
- `sandbox/fixtures/mock_emails.json`
- `sandbox/fixtures/mock_events.json`
- `sandbox/fixtures/mock_messages.json`
