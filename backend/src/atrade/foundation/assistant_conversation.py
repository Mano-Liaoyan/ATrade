"""The conversation of a request on port 8001 (docs/architecture/assistant.md 25.3.2).

The assistant service sends the conversation ID in the header `X-ATrade-Conversation-Id` with each request. The
routes that record the conversation (a strategy version save and a backtest start) read it with the dependency of
`create_conversation_dependency`. A request without the header gets FastAPI's 422 body. A request with the ID of a
conversation that does not exist gets 422 with a text `detail`.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Final

from fastapi import Header, HTTPException, status

CONVERSATION_HEADER: Final = "X-ATrade-Conversation-Id"

# True when the conversation exists. app/ gives the check of the assistant capability.
type ConversationCheck = Callable[[int], Awaitable[bool]]


def create_conversation_dependency(conversation_exists: ConversationCheck) -> Callable[[int], Awaitable[int]]:
    async def read_conversation_id(
        conversation_id: Annotated[int, Header(alias=CONVERSATION_HEADER, gt=0)],
    ) -> int:
        if not await conversation_exists(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Conversation {conversation_id} does not exist.",
            )
        return conversation_id

    return read_conversation_id
