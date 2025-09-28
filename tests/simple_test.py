import sys
import os
from datetime import datetime, date
from unittest.mock import patch
import pandas as pd

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import get_todays_events

# Test calendar configurations using only working local files
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
            print(f"Test calendar file not found: {file_path}")
            return type('MockResponse', (), {
                'content': b'',
                'raise_for_status': lambda self: None
            })()
    else:
        # Fallback to original behavior for non-file URLs
        import requests
        return requests.get(url, timeout=timeout)

def test_get_todays_events_simple():
    """Simple test of get_todays_events function using working local calendar files"""
    print("Testing get_todays_events() function with working calendars...")
    print(f"Today's date: {date.today()}")
    print("-" * 50)

    # Mock the ICAL_FEELS to use only working local test files
    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file):

        try:
            # Call the function
            events_df = get_todays_events()

            # Display results
            if events_df.empty:
                print("No events found for today.")
            else:
                print(f"Found {len(events_df)} events for today:")
                print()
                print("Events:")
                print("-" * 40)
                for _, event in events_df.iterrows():
                    print(f"📅 {event['calendar']} ({event['text_color']})")
                    print(f"   {event['title']}")
                    print(f"   {event['time_display']}")
                    print()

            return events_df

        except Exception as e:
            print(f"Error during test: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    # Run the simple test
    events = test_get_todays_events_simple()

    # Also show the structure of what we get back
    if not events.empty:
        print("\nDataFrame structure:")
        print("-" * 50)
        print(f"Shape: {events.shape}")
        print(f"Columns: {list(events.columns)}")
        print("\nSample event data:")
        print(events.iloc[0].to_dict() if len(events) > 0 else "No events")