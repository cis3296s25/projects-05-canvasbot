import pytest
import sys
import os
import json
import asyncio
from unittest.mock import MagicMock, patch, mock_open, AsyncMock

# Add root dir to sys.path for module access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cogs.set_colors import ColorPickerView, CanvasColorCog, GOOGLE_COLORS

@pytest.fixture
def fake_courses():
    return [
        {"id": 101, "name": "Intro to Magic"},
        {"id": 202, "name": "Dark Arts 101"},
    ]



@pytest.mark.asyncio
async def test_color_picker_view_creates_dropdowns(fake_courses):
    view = ColorPickerView(fake_courses, user_id="123")
    assert len(view.children) == len(fake_courses), "Should create one Select per course"


@patch("builtins.open", new_callable=mock_open)
@patch("os.makedirs")
@patch("os.path.exists", return_value=False)
@pytest.mark.asyncio
async def test_on_timeout_creates_file(mock_exists, mock_makedirs, mock_file):
    view = ColorPickerView([{"id": 303, "name": "Test Class"}], user_id="999")
    view.responses = {
        "303": {
            "name": "Test Class",
            "color": "5"
        }
    }

    await view.on_timeout()

    mock_makedirs.assert_called_once_with("course_colors")
    mock_file.assert_called_once_with("course_colors/999.json", "w")
    handle = mock_file()
    handle.write.assert_called()  # Confirm write occurred
