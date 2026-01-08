"""
Pytest configuration for AI Workflow Agent tests.
"""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_emails():
    """Sample emails for testing."""
    return [
        {
            "id": "1",
            "sender": "boss@company.com",
            "subject": "URGENT: Meeting tomorrow",
            "body": "Please confirm attendance",
        },
        {
            "id": "2",
            "sender": "newsletter@marketing.com",
            "subject": "Weekly Newsletter",
            "body": "Your weekly update",
        },
        {
            "id": "3",
            "sender": "hr@company.com",
            "subject": "Action Required: Update info",
            "body": "Please update your information",
        },
    ]


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return [
        {"id": 1, "name": "Alice", "department": "Engineering", "value": 100},
        {"id": 2, "name": "Bob", "department": "Marketing", "value": 80},
        {"id": 3, "name": "Charlie", "department": "Engineering", "value": 95},
    ]
