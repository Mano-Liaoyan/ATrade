"""The save of a strategy version: the checks before save, then the append (docs/architecture/strategy.md 9.3).

The HTTP route of port 8000 saves with the source user. Port 8001 saves with the source ai_assistant and the
conversation ID through `save_ai_assistant_version` (docs/architecture/assistant.md 25.5).
"""

from datetime import datetime

import psycopg

from atrade.strategy import strategy_store
from atrade.strategy.code_checks import CodeProblem, check_strategy_code


async def save_checked_version(
    *, database_url: str, strategy_id: int, content: strategy_store.VersionContent, created_at_utc: datetime
) -> strategy_store.SavedVersion | list[CodeProblem] | None:
    """The saved version, or the problems when a check blocks the save, or None when the strategy is missing."""
    problems = await check_strategy_code(content.code)
    if problems:
        return problems
    async with await psycopg.AsyncConnection.connect(database_url) as connection:
        saved = await strategy_store.save_version(
            connection, strategy_id=strategy_id, content=content, created_at_utc=created_at_utc
        )
        await connection.commit()
    return saved


async def save_ai_assistant_version(
    *, database_url: str, strategy_id: int, code: str, conversation_id: int, created_at_utc: datetime
) -> strategy_store.SavedVersion | list[CodeProblem] | None:
    """Saves code of the AI assistant with the source ai_assistant and its conversation.

    Returns the problems when a check blocks the save, and None when the strategy is missing. When the code is the
    same as the latest version, no new version is made and the latest version comes back.
    """
    content = strategy_store.VersionContent(
        code=code, source="ai_assistant", rules=None, conversation_id=conversation_id
    )
    return await save_checked_version(
        database_url=database_url, strategy_id=strategy_id, content=content, created_at_utc=created_at_utc
    )
