import pytest
import json
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock, mock_open 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cogs.planner_integration import planner

@pytest.fixture
def interaction():
    mock = MagicMock()
    mock.user.id = 123
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    return mock

@pytest.fixture
def planner_cog():
    mock_client = MagicMock()
    return planner(mock_client)

@patch("builtins.open", new_callable=mock_open, read_data=json.dumps({
    "token": "test", "refresh_token": "test", "client_id": "id", "client_secret": "secret", "token_uri": "uri", "scopes": []
}))
@patch("cogs.planner_integration.build") 
@pytest.mark.asyncio
async def test_calendar_test_success(mock_build, mock_open, interaction, planner_cog):
    # Setup Google API mock
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {
        "items": [{"start": {"dateTime": "2025-01-01T12:00:00"}, "summary": "Test Event"}]
    }
    mock_build.return_value = mock_service

    await planner_cog.calendar_test(interaction)

    interaction.followup.send.assert_called_once()
    args, kwargs = interaction.followup.send.call_args
    assert "Upcoming events" in args[0]
    print("✅ test_calendar_test_success passed")

