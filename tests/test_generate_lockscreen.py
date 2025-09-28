import sys
import os
import pytest
import pandas as pd
from datetime import datetime, date
from unittest.mock import patch
from PIL import Image

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import generate_lockscreen_image, pick_random_background, get_todays_events

def create_sample_events():
    """Create sample events data for testing"""
    return pd.DataFrame([
        {
            'calendar': 'personal',
            'text_color': 'green',
            'title': 'Morning Meeting',
            'start_time': datetime(2025, 9, 27, 9, 0),
            'end_time': datetime(2025, 9, 27, 10, 0),
            'start_str': '09:00',
            'end_str': '10:00',
            'time_display': '09:00-10:00'
        },
        {
            'calendar': 'kbr',
            'text_color': 'red',
            'title': 'Project Review',
            'start_time': datetime(2025, 9, 27, 14, 0),
            'end_time': datetime(2025, 9, 27, 15, 30),
            'start_str': '14:00',
            'end_str': '15:30',
            'time_display': '14:00-15:30'
        },
        {
            'calendar': 'personal',
            'text_color': 'green',
            'title': 'All Day Event - Holiday',
            'start_time': date(2025, 9, 27),
            'end_time': None,
            'start_str': 'All Day',
            'end_str': '',
            'time_display': 'All Day'
        },
        {
            'calendar': 'kbr',
            'text_color': 'red',
            'title': 'Very Long Event Title That Should Be Truncated Because It Is Too Long',
            'start_time': datetime(2025, 9, 27, 16, 0),
            'end_time': datetime(2025, 9, 27, 17, 0),
            'start_str': '16:00',
            'end_str': '17:00',
            'time_display': '16:00-17:00'
        }
    ])

def test_generate_lockscreen_image_basic():
    """Test basic functionality of generate_lockscreen_image"""
    # Get a background image
    background = pick_random_background()

    # Create sample events
    events = create_sample_events()

    # Generate lockscreen image with unique name in test folder
    import time
    import os
    os.makedirs("tests/outputs", exist_ok=True)
    test_output = f"tests/outputs/test_basic_{int(time.time())}.png"
    output_path = generate_lockscreen_image(events, background, test_output)

    # Check that output file was created
    assert os.path.exists(output_path), "Output image file should be created"
    assert output_path.endswith('.png'), "Output should be a PNG file"

    # Check that the file is a valid image
    with Image.open(output_path) as img:
        assert img.size == (1290, 2796), "Output image should have iPhone dimensions"
        assert img.mode in ['RGB', 'RGBA'], "Output image should be RGB or RGBA"

    # Keep the image for visual inspection
    print(f"Generated test image: {output_path}")

def test_generate_lockscreen_image_empty_events():
    """Test generate_lockscreen_image with no events"""
    # Get a background image
    background = pick_random_background()

    # Create empty events DataFrame
    empty_events = pd.DataFrame(columns=['calendar', 'text_color', 'title', 'start_time', 'end_time', 'start_str', 'end_str', 'time_display'])

    # Generate lockscreen image in test folder
    import time
    import os
    os.makedirs("tests/outputs", exist_ok=True)
    test_output = f"tests/outputs/test_empty_{int(time.time())}.png"
    output_path = generate_lockscreen_image(empty_events, background, test_output)

    # Check that output file was created
    assert os.path.exists(output_path), "Output image file should be created even with no events"

    # Keep the image for visual inspection
    print(f"Generated test image: {output_path}")

def test_generate_lockscreen_image_return_type():
    """Test that generate_lockscreen_image returns correct type"""
    background = pick_random_background()
    events = create_sample_events()

    import time
    import os
    os.makedirs("tests/outputs", exist_ok=True)
    test_output = f"tests/outputs/test_return_{int(time.time())}.png"
    output_path = generate_lockscreen_image(events, background, test_output)

    # Should return a string path
    assert isinstance(output_path, str), "Function should return a string path"
    assert output_path.endswith('.png'), "Path should end with .png"

    # Keep the image for visual inspection
    print(f"Generated test image: {output_path}")

def test_generate_lockscreen_image_with_all_day_events():
    """Test handling of all-day events specifically"""
    background = pick_random_background()

    # Create events with only all-day events
    all_day_events = pd.DataFrame([
        {
            'calendar': 'personal',
            'text_color': 'green',
            'title': 'Holiday',
            'start_time': date(2025, 9, 27),
            'end_time': None,
            'start_str': 'All Day',
            'end_str': '',
            'time_display': 'All Day'
        },
        {
            'calendar': 'kbr',
            'text_color': 'red',
            'title': 'Conference',
            'start_time': date(2025, 9, 27),
            'end_time': None,
            'start_str': 'All Day',
            'end_str': '',
            'time_display': 'All Day'
        }
    ])

    import time
    import os
    os.makedirs("tests/outputs", exist_ok=True)
    test_output = f"tests/outputs/test_allday_{int(time.time())}.png"
    output_path = generate_lockscreen_image(all_day_events, background, test_output)

    # Check that output file was created
    assert os.path.exists(output_path), "Output image file should be created with all-day events"

    # Keep the image for visual inspection
    print(f"Generated test image: {output_path}")

def test_generate_lockscreen_image_integration():
    """Integration test using real calendar data"""
    from test_get_todays_events import WORKING_TEST_FEEDS, read_local_calendar_file

    # Mock to use local test files and specific date with events
    target_date = date(2025, 9, 26)  # Date that has events

    class MockDate(date):
        @classmethod
        def today(cls):
            return target_date

    with patch('main.ICAL_FEELS', WORKING_TEST_FEEDS), \
         patch('main.requests.get', side_effect=read_local_calendar_file), \
         patch('main.date', MockDate):

        # Get real events
        events = get_todays_events()

        # Get background
        background = pick_random_background()

        # Generate lockscreen in test folder
        import time
        import os
        os.makedirs("tests/outputs", exist_ok=True)
        test_output = f"tests/outputs/test_integration_{int(time.time())}.png"
        output_path = generate_lockscreen_image(events, background, test_output)

        # Verify output
        assert os.path.exists(output_path), "Integration test should create output file"

        # Check file size (should be reasonable for a PNG)
        file_size = os.path.getsize(output_path)
        assert file_size > 100000, "Output file should be substantial (>100KB)"  # Basic sanity check

        # Keep the image for visual inspection
        print(f"Generated test image: {output_path}")
        print(f"Events used: {len(events)} events found")

def test_generate_lockscreen_image_different_colors():
    """Test that different text colors are handled"""
    background = pick_random_background()

    # Create events with different colors
    colorful_events = pd.DataFrame([
        {
            'calendar': 'cal1',
            'text_color': 'green',
            'title': 'Green Event',
            'start_time': datetime(2025, 9, 27, 9, 0),
            'end_time': datetime(2025, 9, 27, 10, 0),
            'start_str': '09:00',
            'end_str': '10:00',
            'time_display': '09:00-10:00'
        },
        {
            'calendar': 'cal2',
            'text_color': 'red',
            'title': 'Red Event',
            'start_time': datetime(2025, 9, 27, 11, 0),
            'end_time': datetime(2025, 9, 27, 12, 0),
            'start_str': '11:00',
            'end_str': '12:00',
            'time_display': '11:00-12:00'
        },
        {
            'calendar': 'cal3',
            'text_color': 'blue',
            'title': 'Blue Event',
            'start_time': datetime(2025, 9, 27, 13, 0),
            'end_time': datetime(2025, 9, 27, 14, 0),
            'start_str': '13:00',
            'end_str': '14:00',
            'time_display': '13:00-14:00'
        }
    ])

    import time
    import os
    os.makedirs("tests/outputs", exist_ok=True)
    test_output = f"tests/outputs/test_colors_{int(time.time())}.png"
    output_path = generate_lockscreen_image(colorful_events, background, test_output)

    # Should handle different colors without error
    assert os.path.exists(output_path), "Should handle different text colors"

    # Keep the image for visual inspection
    print(f"Generated test image: {output_path}")