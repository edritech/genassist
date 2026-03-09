import logging

import pytest

from app.tasks.zendesk_tasks import analyze_zendesk_tickets_async_with_scope

logger = logging.getLogger(__name__)


@pytest.mark.asyncio(scope="session")
async def test_zendesk_task():
    result = await analyze_zendesk_tickets_async_with_scope()
    assert result is not None, "Zendesk task should return a result"
    assert result.get("status") == "completed", "Zendesk task should complete successfully"
