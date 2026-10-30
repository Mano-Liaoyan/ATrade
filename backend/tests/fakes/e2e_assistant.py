"""The fake assistant service of the e2e server (tests/e2e_server.py). No pi and no model provider.

The text of a prompt selects the answer:
- "wait": streams one part, then waits for the abort ("Stop").
- "change": a save_strategy_version tool step, a new strategy version of the AI assistant, and a diff card.
- "backtest": a run_backtest tool step with a finished backtest, and a metric card.
- "notitle": a normal answer, but the title generation fails.
- other text: a streamed answer.
The answer ends with the model of the prompt and the name of its credential. The messages are kept, so a reload
shows them.
"""

import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import anyio
import psycopg

from atrade.assistant import (
    AssistantServiceError,
    BacktestFinished,
    ConversationMessage,
    CredentialSummary,
    MessageEnd,
    ModelSelection,
    ProviderModel,
    ProviderSummary,
    RunEvent,
    StrategyVersionSaved,
    TextDelta,
    ToolStep,
)
from tests.fakes.assistant import FakeAssistantService

STREAM_PAUSE_SECONDS = 0.05
E2E_BACKTEST_START_UTC = datetime(2026, 3, 2, tzinfo=UTC)


def make_credential(credential_id: str, name: str) -> CredentialSummary:
    return CredentialSummary(
        id=credential_id,
        name=name,
        provider="openai",
        type="api_key",
        key_last4="1234",
        state="ready",
        state_message=None,
    )


class E2EAssistantService(FakeAssistantService):
    def __init__(self, database_url: str) -> None:
        super().__init__()
        self.database_url = database_url
        self.providers = [
            ProviderSummary(
                id="openai",
                name="OpenAI",
                login_methods=["api_key"],
                models=[ProviderModel(id="gpt-a", name="GPT A"), ProviderModel(id="gpt-b", name="GPT B")],
            )
        ]
        self.credentials = [make_credential("work", "Work key"), make_credential("home", "Home key")]
        self.abort_events: dict[int, anyio.Event] = {}
        self.first_texts: dict[int, str] = {}

    def credential_name(self, credential_id: str) -> str:
        return next((item.name for item in self.credentials if item.id == credential_id), credential_id)

    def answer_end(self, conversation_id: int, text: str, selection: ModelSelection) -> MessageEnd:
        end = MessageEnd(
            text=text,
            provider=selection.provider,
            model=selection.model,
            credential_name=self.credential_name(selection.credential_id),
        )
        self.messages.setdefault(conversation_id, []).append(
            ConversationMessage(
                role="assistant",
                text=text,
                provider=end.provider,
                model=end.model,
                credential_name=end.credential_name,
            )
        )
        return end

    async def run(
        self, conversation_id: int, text: str, selection: ModelSelection, system_prompt: str
    ) -> AsyncIterator[RunEvent]:
        self.runs.append((conversation_id, text, selection))
        self.system_prompts.append(system_prompt)
        self.first_texts.setdefault(conversation_id, text)
        self.messages.setdefault(conversation_id, []).append(
            ConversationMessage(role="user", text=text, provider=None, model=None, credential_name=None)
        )
        if "wait" in text:
            abort_event = anyio.Event()
            self.abort_events[conversation_id] = abort_event
            yield TextDelta(text="Working on it")
            await abort_event.wait()
            return
        if "change" in text:
            async for event in self.save_version(conversation_id):
                yield event
            yield self.answer_end(conversation_id, "I saved a new version.", selection)
            return
        if "backtest" in text:
            async for event in self.run_backtest(conversation_id):
                yield event
            yield self.answer_end(conversation_id, "The backtest finished.", selection)
            return
        answer = "Hello from the fake AI assistant."
        for part in ("Hello ", "from the fake ", "AI assistant."):
            await anyio.sleep(STREAM_PAUSE_SECONDS)
            yield TextDelta(text=part)
        yield self.answer_end(conversation_id, answer, selection)

    async def abort(self, conversation_id: int) -> None:
        self.aborts.append(conversation_id)
        abort_event = self.abort_events.pop(conversation_id, None)
        if abort_event is not None:
            abort_event.set()

    async def generate_title(self, conversation_id: int, selection: ModelSelection) -> str:
        self.title_requests.append((conversation_id, selection))
        if "notitle" in self.first_texts.get(conversation_id, ""):
            message = "The model did not answer."
            raise AssistantServiceError(message)
        return f"Title of {self.first_texts.get(conversation_id, 'the conversation')}"

    async def save_version(self, conversation_id: int) -> AsyncIterator[RunEvent]:
        yield ToolStep(
            tool_call_id="save", tool_name="save_strategy_version", status="running", backtest_id=None, backtest_status=None
        )
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            cursor = await connection.execute(
                """
                SELECT version.strategy_id, version.version_number, version.code
                FROM assistant_conversation AS conversation
                JOIN strategy_version AS version ON version.strategy_id = conversation.strategy_id
                WHERE conversation.id = %(conversation_id)s
                ORDER BY version.version_number DESC
                LIMIT 1
                """,
                {"conversation_id": conversation_id},
            )
            row = await cursor.fetchone()
            assert row is not None
            strategy_id, last_number, last_code = row
            version_number = int(last_number) + 1
            code = f"{last_code}# Version {version_number} of the AI assistant.\n"
            cursor = await connection.execute(
                """
                INSERT INTO strategy_version (strategy_id, version_number, code, code_sha256, created_at_utc, source,
                    conversation_id)
                VALUES (%(strategy_id)s, %(version_number)s, %(code)s, %(code_sha256)s, %(now)s, 'ai_assistant',
                    %(conversation_id)s)
                RETURNING id
                """,
                {
                    "strategy_id": strategy_id,
                    "version_number": version_number,
                    "code": code,
                    "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
                    "now": datetime.now(UTC),
                    "conversation_id": conversation_id,
                },
            )
            version_row = await cursor.fetchone()
            assert version_row is not None
        yield ToolStep(
            tool_call_id="save",
            tool_name="save_strategy_version",
            status="succeeded",
            backtest_id=None,
            backtest_status=None,
        )
        yield StrategyVersionSaved(
            strategy_id=int(strategy_id), strategy_version_id=int(version_row[0]), version_number=version_number
        )

    async def run_backtest(self, conversation_id: int) -> AsyncIterator[RunEvent]:
        async with await psycopg.AsyncConnection.connect(self.database_url, autocommit=True) as connection:
            cursor = await connection.execute(
                """
                INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                    paper_capital_usd, status, created_at_utc, started_at_utc, ended_at_utc, final_equity_usd,
                    total_return_percent, max_drawdown_percent, trade_count, sharpe_ratio, win_rate_percent,
                    conversation_id)
                SELECT version.id, 'E2EAI', 'ARCA', 'USD', '1-DAY', %(start)s, %(end)s, 10000, 'finished', %(now)s,
                    %(now)s, %(now)s, 11000, 10, 5, 4, 1.25, 50, %(conversation_id)s
                FROM assistant_conversation AS conversation
                JOIN strategy_version AS version ON version.strategy_id = conversation.strategy_id
                WHERE conversation.id = %(conversation_id)s
                ORDER BY version.version_number DESC
                LIMIT 1
                RETURNING id
                """,
                {
                    "start": E2E_BACKTEST_START_UTC,
                    "end": E2E_BACKTEST_START_UTC + timedelta(days=30),
                    "now": datetime.now(UTC),
                    "conversation_id": conversation_id,
                },
            )
            row = await cursor.fetchone()
            assert row is not None
        backtest_id = int(row[0])
        for status in ("queued", "running", "finished"):
            await anyio.sleep(STREAM_PAUSE_SECONDS)
            yield ToolStep(
                tool_call_id="backtest",
                tool_name="run_backtest",
                status="succeeded" if status == "finished" else "running",
                backtest_id=backtest_id,
                backtest_status=status,
            )
        yield BacktestFinished(backtest_id=backtest_id)

