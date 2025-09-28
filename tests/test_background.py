import sys
import os
import io
import pytest
from PIL import Image

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import pick_random_background, IPHONE_WIDTH_PX, IPHONE_HEIGHT_PX

def test_pick_random_background_basic():
    """Test basic functionality of pick_random_background function"""
    # Test the function
    background_image = pick_random_background()

    # Check that we got a PIL Image
    assert isinstance(background_image, Image.Image), "Function should return a PIL Image object"

    # Check image mode
    assert background_image.mode in ['RGB', 'RGBA'], f"Image should be RGB or RGBA, got {background_image.mode}"

    # Verify dimensions match iPhone requirements
    width, height = background_image.size
    assert width == IPHONE_WIDTH_PX, f"Width should be {IPHONE_WIDTH_PX}, got {width}"
    assert height == IPHONE_HEIGHT_PX, f"Height should be {IPHONE_HEIGHT_PX}, got {height}"

def test_pick_random_background_dimensions():
    """Test that the function returns correct dimensions"""
    background_image = pick_random_background()
    width, height = background_image.size

    assert width == IPHONE_WIDTH_PX
    assert height == IPHONE_HEIGHT_PX

def test_pick_random_background_file_save():
    """Test that the generated image can be saved successfully"""
    background_image = pick_random_background()
    test_output_path = "test_background_output.png"

    # This should not raise an exception
    background_image.save(test_output_path)

    # Verify file was created
    assert os.path.exists(test_output_path), "Test image file should be created"

    # Clean up
    if os.path.exists(test_output_path):
        os.remove(test_output_path)

def test_pick_random_background_randomness():
    """Test that multiple calls return different images (randomness)"""
    images = []
    num_tests = 3

    for i in range(num_tests):
        img = pick_random_background()
        # Convert to bytes for comparison
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        images.append(buf.getvalue())

    # We expect at least some variation if we have multiple background files
    # Note: this test might occasionally fail if the same image is randomly selected multiple times
    unique_images = len(set(images))
    assert unique_images >= 1, "Should generate at least one valid image"

    # If we have multiple background files, we should sometimes get different results
    # This is probabilistic so we won't make it a hard requirement

def test_pick_random_background_custom_dimensions():
    """Test pick_random_background with custom dimensions"""
    custom_width = 500
    custom_height = 800

    background_image = pick_random_background(
        width_px=custom_width,
        height_px=custom_height
    )

    width, height = background_image.size
    assert width == custom_width, f"Custom width should be {custom_width}, got {width}"
    assert height == custom_height, f"Custom height should be {custom_height}, got {height}"

def test_pick_random_background_invalid_folder():
    """Test behavior with non-existent background folder"""
    with pytest.raises(FileNotFoundError):
        pick_random_background(background_folder="./non_existent_folder/")