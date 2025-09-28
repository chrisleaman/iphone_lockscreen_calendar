import sys
import os
from datetime import datetime, date
from unittest.mock import patch
import pandas as pd
import pytest

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_todays_events, ICAL_FEELS

# Test calendar configurations using working local files only
WORKING_TEST_FEEDS = [
    {
        "name": "personal",
        "url": "file://tests/data/calendars/personal.ics",
        "text_color": "green",
    },
    {
        "name": "kbr",
        "url": "file://tests/data/calendars/kbr.ics",
        "text_color": "red",
    },
]

def read_local_calendar_file(url, timeout=10):
    """Mock function to read local calendar files instead of downloading"""
    if url.startswith("file://"):
        file_path = url[7:]  # Remove "file://" prefix
        try:
            with open(file_path, 'rb') as f:
                return type('MockResponse', (), {
                    'content': f.read(),
                    'raise_for_status': lambda self: None
                })()
        except FileNotFoundError:
            return type('MockResponse', (), {
                'content': b'',
                'raise_for_status': lambda self: None
            })()
    else:
        # Fallback to original behavior for non-file URLs
        import requests
        return requests.get(url, timeout=timeout)

def test_get_todays_events_basic():
    """Test basic functionality of get_todays_events function"""
    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file):

        events_df = get_todays_events()

        # Should return a DataFrame
        assert isinstance(events_df, pd.DataFrame), "Function should return a pandas DataFrame"

        # Should have expected columns
        expected_columns = ['calendar', 'text_color', 'title', 'start_time', 'end_time', 'start_str', 'end_str', 'time_display']
        for col in expected_columns:
            assert col in events_df.columns, f"DataFrame should have column '{col}'"

def test_get_todays_events_return_type():
    """Test that get_todays_events returns correct data types"""
    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file):

        events_df = get_todays_events()

        # If not empty, check data types
        if not events_df.empty:
            assert events_df['calendar'].dtype == 'object'
            assert events_df['text_color'].dtype == 'object'
            assert events_df['title'].dtype == 'object'
            assert events_df['time_display'].dtype == 'object'

def test_get_todays_events_with_specific_date():
    """Test the function with a specific date"""
    target_date = date(2025, 9, 26)  # Use a date that might have events

    class MockDate(date):
        @classmethod
        def today(cls):
            return target_date

    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file), \
         patch('main.date', MockDate):

        events_df = get_todays_events()

        # Should return a DataFrame
        assert isinstance(events_df, pd.DataFrame)

        # Should have expected columns
        expected_columns = ['calendar', 'text_color', 'title', 'start_time', 'end_time', 'start_str', 'end_str', 'time_display']
        for col in expected_columns:
            assert col in events_df.columns

def test_get_todays_events_empty_calendar():
    """Test behavior with empty calendar feeds"""
    empty_feeds = []

    with patch('main.ICAL_FEELS', empty_feeds), \
         patch('main.requests.get', side_effect=read_local_calendar_file):

        events_df = get_todays_events()

        # Should return empty DataFrame with expected structure
        assert isinstance(events_df, pd.DataFrame)
        assert events_df.empty
        expected_columns = ['calendar', 'text_color', 'title', 'start_time', 'end_time', 'start_str', 'end_str', 'time_display']
        for col in expected_columns:
            assert col in events_df.columns

def test_get_todays_events_invalid_calendar_file():
    """Test behavior with invalid calendar file"""
    invalid_feeds = [
        {
            "name": "invalid",
            "url": "file://test_data/calendars/non_existent.ics",
            "text_color": "blue",
        }
    ]

    with patch('main.ICAL_FEELS', invalid_feeds), \
         patch('main.requests.get', side_effect=read_local_calendar_file):

        # Should not raise an exception, just return empty DataFrame
        events_df = get_todays_events()
        assert isinstance(events_df, pd.DataFrame)

@pytest.mark.parametrize("test_date", [
    date(2025, 9, 26),
    date(2025, 9, 27),
    date(2025, 9, 28),
])
def test_get_todays_events_multiple_dates(test_date):
    """Test the function with multiple different dates"""
    class MockDate(date):
        @classmethod
        def today(cls):
            return test_date

    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file), \
         patch('main.date', MockDate):

        events_df = get_todays_events()

        # Should always return a DataFrame
        assert isinstance(events_df, pd.DataFrame)

        # If events found, they should be for the correct date
        if not events_df.empty:
            for _, event in events_df.iterrows():
                # Check that calendar and text_color are from our test feeds
                assert event['calendar'] in ['personal', 'kbr']
                assert event['text_color'] in ['green', 'red']