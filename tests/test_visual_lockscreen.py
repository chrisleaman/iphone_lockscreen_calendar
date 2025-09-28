import sys
import os
from datetime import datetime, date
from unittest.mock import patch

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import generate_lockscreen_image, pick_random_background, get_todays_events
from test_get_todays_events import WORKING_TEST_FEEDS, read_local_calendar_file

def create_visual_test():
    """Create a visual test of the lockscreen generation"""
    print("Creating visual test of lockscreen generation...")

    # Test with a specific date that might have events
    target_date = date(2025, 9, 26)  # Date that showed events in previous tests

    class MockDate(date):
        @classmethod
        def today(cls):
            return target_date

    # Mock to use local test files and specific date
    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file), \
         patch('main.date', MockDate):

        # Get events from calendar
        print("Fetching events...")
        events = get_todays_events()
        print(f"Found {len(events)} events")

        if not events.empty:
            print("\nEvents to be displayed:")
            for _, event in events.iterrows():
                print(f"  {event['time_display']} - {event['title']} ({event['calendar']}, {event['text_color']})")

        # Get background image
        print("\nSelecting background image...")
        background = pick_random_background()
        print(f"Background image: {background.size}")

        # Generate lockscreen
        print("\nGenerating lockscreen image...")
        output_path = generate_lockscreen_image(events, background)

        print(f"SUCCESS: Lockscreen image saved to: {output_path}")

        # Check file info
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"  File size: {file_size:,} bytes")

            from PIL import Image
            with Image.open(output_path) as img:
                print(f"  Dimensions: {img.size}")
                print(f"  Mode: {img.mode}")

        return output_path

if __name__ == "__main__":
    result = create_visual_test()
    print(f"\nVisual test completed. Check the generated image: {result}")
    print("You can open this file to see how the calendar events look on the background!")