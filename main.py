import requests
import pandas as pd
from datetime import datetime, date
from icalendar import Calendar
from pytz import timezone
import random
import os
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from loguru import logger
import sys
import recurring_ical_events
import toml
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def load_config(config_path="./inputs/config.toml"):
    """Load configuration from TOML file"""
    try:
        with open(config_path, 'r') as f:
            config = toml.load(f)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

# Load configuration
config = load_config()

# Configure loguru for simple console logging
# logger.remove()  # Remove default handler
# logger.add(
#     sys.stdout,
#     format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
#     level=config.get("behavior", {}).get("log_level", "DEBUG"),
#     colorize=True
# )

# Extract configuration values
IPHONE_HEIGHT_PX = config["display"]["height_px"]
IPHONE_WIDTH_PX = config["display"]["width_px"]

BACKGROUND_FOLDER = os.path.join("./inputs", config["paths"]["backgrounds_folder"])

AWS_ACCESS_KEY_ID = config["aws"]["access_key_id"]
AWS_SECRET_ACCESS_KEY = config["aws"]["secret_access_key"]
AWS_BUCKET_NAME = config["aws"]["bucket_name"]

ICAL_FEELS = config["calendars"]


def run():
    logger.info("Starting iPhone lockscreen calendar generation")

    logger.info("Fetching today's events from calendars")
    events = get_todays_events()
    logger.info(f"Found {len(events)} events for today")

    logger.info("Selecting random background image")
    background_image = pick_random_background()
    logger.info(f"Selected background image with dimensions: {background_image.size}")

    logger.info("Generating lockscreen image with events overlay")
    lockscreen_image = generate_lockscreen_image(
        events=events, background_image=background_image
    )
    logger.success(f"Lockscreen image generated: {lockscreen_image}")

    logger.info("Uploading to AWS S3")
    upload_success = upload_to_s3(lockscreen_image=lockscreen_image)

    if upload_success:
        logger.success("Lockscreen calendar generation completed!")
    else:
        logger.warning("Lockscreen generation completed but S3 upload failed")

def get_todays_events():
    """
    Get today's events from each icalendar. Store the start and finish time and
    keep track of which event belongs to which calendar and the relevant text color.
    Return in a pandas dataframe
    """
    # Use configured timezone for determining "today"
    local_tz = timezone(config["timezone"]["timezone"])
    now_local = datetime.now(local_tz)
    today_local = now_local.date()
    logger.debug(f"Fetching events for date: {today_local} ({local_tz.zone} time)")
    logger.debug(f"Current local time: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    all_events = []

    for cal_config in ICAL_FEELS:
        cal_name = cal_config['name']
        logger.debug(f"Processing calendar: {cal_name}")
        try:
            # Fetch the iCal data
            logger.debug(f"Downloading calendar data from: {cal_config['url']}")
            response = requests.get(cal_config['url'], timeout=10)
            response.raise_for_status()

            # Parse the iCal data
            calendar = Calendar.from_ical(response.content)
            logger.debug(f"Successfully parsed calendar: {cal_name}")

            # Get today's events
            events = recurring_ical_events.of(calendar).at(today_local)
            for e in events:
                summary = str(e.get("SUMMARY", "No Title"))

                start_time = e["DTSTART"]
                end_time = e["DTEND"]

                # Ensure times have time and are tz localised

                # Convert timezone-aware events to Brisbane time for date comparison
                if hasattr(start_time.dt, 'tzinfo') and start_time.dt.tzinfo:
                    # Convert to Brisbane time
                    start_local = start_time.dt.astimezone(local_tz)
                    logger.debug(f"  Event timezone conversion: {start_time.dt} -> {start_local}")
                else:
                    # Handle naive datetime or date objects (assume they're already in Brisbane time)
                    if hasattr(start_time.dt, 'date'):
                        # Make naive datetime timezone-aware by assuming it's Brisbane time
                        start_local = local_tz.localize(start_time.dt)
                    else:
                        # Date object - create a timezone-aware datetime for consistency
                        start_local = local_tz.localize(datetime.combine(start_time.dt, datetime.min.time()))

                # Convert timezone-aware events to Brisbane time for date comparison
                if hasattr(end_time.dt, 'tzinfo') and end_time.dt.tzinfo:
                    # Convert to Brisbane time
                    end_local = end_time.dt.astimezone(local_tz)
                else:
                    # Handle naive datetime or date objects (assume they're already in Brisbane time)
                    if hasattr(end_time.dt, 'date'):
                        # Make naive datetime timezone-aware by assuming it's Brisbane time
                        end_local = local_tz.localize(end_time.dt)
                    else:
                        # Date object - create a timezone-aware datetime for consistency
                        end_local = local_tz.localize(datetime.combine(end_time.dt, datetime.min.time()))


                start_str = start_local.strftime("%H:%M")
                end_str = end_local.strftime("%H:%M")

                # Add event to list using Brisbane times
                all_events.append(
                    {
                        "calendar": cal_config["name"],
                        "text_color": cal_config["text_color"],
                        "title": summary,
                        "start_time": start_local,
                        "end_time": end_local,
                        "start_str": start_str,
                        "end_str": end_str,
                        "time_display": f"{start_str}-{end_str}"
                        if end_str
                        else start_str,
                    }
                )

        except Exception as e:
            logger.error(f"Error fetching calendar '{cal_name}': {e}")
            continue

    # Convert to DataFrame and sort by start time
    if all_events:
        logger.info(f"Processing {len(all_events)} total events from all calendars")
        df = pd.DataFrame(all_events)

        # Format strings
        logger.debug("Cleaning event titles")
        df.title = df.title.str.replace(r'^S: ', '', regex=True)
        df.title = df.title.str.replace(r'^D: ', '', regex=True)

        # Sort by start time, handling all-day events
        df = df.sort_values(['start_time','calendar','title'])

        logger.info(f"Successfully processed and sorted {len(df)} events")
        return df
    else:
        logger.warning("No events found for today")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=['calendar', 'text_color', 'title', 'start_time', 'end_time', 'start_str', 'end_str', 'time_display'])

def pick_random_background(
        background_folder=BACKGROUND_FOLDER,
        width_px=IPHONE_WIDTH_PX,
        height_px=IPHONE_HEIGHT_PX,
):
    """
    Pick a random background image from the folder, crop to iPhone dimensions,
    and return the PIL Image object.
    """
    logger.debug(f"Looking for background images in: {background_folder}")

    # Get all PNG files from the background folder
    if not os.path.exists(background_folder):
        logger.error(f"Background folder not found: {background_folder}")
        raise FileNotFoundError(f"Background folder not found: {background_folder}")

    background_files = [f for f in os.listdir(background_folder)
                       if f.lower().endswith('.png')]

    if not background_files:
        logger.error(f"No PNG files found in {background_folder}")
        raise FileNotFoundError(f"No PNG files found in {background_folder}")

    logger.info(f"Found {len(background_files)} background images")

    # Set random seed based on today's date for consistent daily backgrounds
    today = date.today()
    seed = int(today.strftime('%Y%m%d'))
    random.seed(seed)
    logger.debug(f"Set random seed to {seed} based on date {today}")

    # Pick a random background file (deterministic for the day)
    selected_file = random.choice(background_files)
    file_path = os.path.join(background_folder, selected_file)
    logger.info(f"Selected random background: {selected_file}")

    # Load the image
    logger.debug(f"Loading image from: {file_path}")
    image = Image.open(file_path)

    # Get original dimensions
    orig_width, orig_height = image.size
    logger.debug(f"Original image dimensions: {orig_width}x{orig_height}")

    # Calculate the scale factor to cover the iPhone dimensions
    # We want to crop to fit, so we need to scale to cover the entire area
    scale_width = width_px / orig_width
    scale_height = height_px / orig_height
    logger.debug(f"Scale factors - width: {scale_width:.3f}, height: {scale_height:.3f}")

    # Use the larger scale factor to ensure we cover the entire iPhone screen
    scale_factor = max(scale_width, scale_height)
    logger.debug(f"Using scale factor: {scale_factor:.3f}")

    # Calculate new dimensions after scaling
    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    logger.debug(f"Scaled dimensions: {new_width}x{new_height}")

    # Resize the image
    logger.debug("Resizing image with LANCZOS resampling")
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Calculate crop coordinates to center the image
    left = (new_width - width_px) // 2
    top = (new_height - height_px) // 2
    right = left + width_px
    bottom = top + height_px
    logger.debug(f"Crop coordinates: left={left}, top={top}, right={right}, bottom={bottom}")

    # Crop to iPhone dimensions
    cropped_image = image.crop((left, top, right, bottom))
    logger.debug(f"Successfully cropped to iPhone dimensions: {cropped_image.size}")

    return cropped_image

def generate_lockscreen_image(events, background_image,
                              output_filename="lockscreen.jpg"):
    """
    Combine events and background image to create a lockscreen calendar image using matplotlib.
    """
    logger.info(f"Starting lockscreen image generation with {len(events) if not events.empty else 0} events")

    # Configure matplotlib for high quality rendering
    logger.debug("Configuring matplotlib settings")
    try:
        plt.rcParams['text.usetex'] = True  # Enable LaTeX if available
        plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath,amssymb,amsfonts}'
        plt.rcParams['font.sans-serif'] = 'Helvetica'
        logger.debug("LaTeX rendering enabled")
    except:
        plt.rcParams['text.usetex'] = False  # Fall back if LaTeX not available
        logger.debug("LaTeX not available, using standard text rendering")

    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 30

    # Convert PIL image to numpy array for matplotlib
    logger.debug("Converting PIL image to numpy array for matplotlib")
    bg_array = np.array(background_image)

    # Create figure with exact iPhone dimensions (convert px to inches at 100 DPI)
    fig_width = IPHONE_WIDTH_PX / 100
    fig_height = IPHONE_HEIGHT_PX / 100
    logger.debug(f"Creating matplotlib figure: {fig_width:.1f}x{fig_height:.1f} inches at 100 DPI")

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=100)

    # Display background image
    logger.debug("Setting background image")
    ax.imshow(bg_array, aspect='equal', extent=[0, IPHONE_WIDTH_PX, 0, IPHONE_HEIGHT_PX])

    # Remove axes
    ax.set_xlim(0, IPHONE_WIDTH_PX)
    ax.set_ylim(0, IPHONE_HEIGHT_PX)
    ax.axis('off')

    # Process events if any exist
    if not events.empty:
        logger.info(f"Processing {len(events)} events for display")

        # Get current time for graying out future events (use configured timezone)
        local_tz = timezone(config["timezone"]["timezone"])
        now = datetime.now(local_tz)
        threshold_hours = config["behavior"]["past_event_threshold_hours"]
        threshold_before_now = now.replace(minute=0, second=0, microsecond=0) - pd.Timedelta(hours=threshold_hours)
        logger.debug(f"Current time: {now.strftime('%H:%M')}, graying out events "
                     f"before: {threshold_before_now.strftime('%H:%M')}")

        # Separate and sort events
        all_day_events = []
        timed_events = []

        for _, event in events.iterrows():

            if (event.start_str =='00:00') & (event.end_str =='00:00'):
                all_day_events.append(event)
            else:
                timed_events.append(event)

        logger.debug(f"Event breakdown - All-day: {len(all_day_events)}, Timed: {len(timed_events)}")

        # Sort timed events by start time
        if timed_events:
            timed_events = sorted(timed_events, key=lambda x: x['start_time'] if hasattr(x['start_time'], 'hour') else datetime.min)
            logger.debug("Sorted timed events by start time")

        # Combine events for table (all-day first, then timed)
        table_rows = []

        # Add all-day events
        for event in all_day_events:
            title = event['title']
            max_len = config["text"]["max_title_length"]
            if len(title) > max_len:
                title = title[:max_len-3] + "..."
            table_rows.append(['', title, event['text_color']])

        # Add timed events
        for event in timed_events:
            # Determine if event should be grayed out
            is_past = False
            if hasattr(event['start_time'], 'hour'):
                event_start = event['start_time']
                # Compare timezone-aware datetimes directly
                if event_start <= threshold_before_now:
                    is_past = True

            # Format time and title
            time_str = event['start_str'] if len(event['start_str']) <= 8 else event['start_str'][:8]
            title = event['title']
            max_len = config["text"]["max_title_length"]
            if len(title) > max_len:
                title = title[:max_len-3] + "..."

            color = 'gray' if is_past else event['text_color']
            table_rows.append([time_str, title, color])

        # Create the table content
        if table_rows:
            logger.info(f"Creating calendar table with {len(table_rows)} rows")

            # Position for the text box (top-aligned) using configuration
            box_x = IPHONE_WIDTH_PX * config["layout"]["box_left_margin"]
            box_top_y = IPHONE_HEIGHT_PX * config["layout"]["box_top_position"]
            box_width = IPHONE_WIDTH_PX * config["layout"]["box_width"]

            # Calculate box height based on number of events using configuration
            line_height = config["layout"]["line_height"]
            padding = config["layout"]["padding"]
            box_height = len(table_rows) * line_height + padding * 2

            # Calculate bottom-left corner position for matplotlib (extends downward from top)
            box_y = box_top_y - box_height

            logger.debug(f"Table dimensions - Top: {box_top_y:.0f}, Bottom-left: ({box_x:.0f}, {box_y:.0f}), Size: {box_width:.0f}x{box_height:.0f}")

            # Create rounded rectangle with 90% alpha black background
            logger.debug("Creating rounded text box background")
            rounded_box = FancyBboxPatch(
                (box_x, box_y), box_width, box_height,
                boxstyle="round,pad=15",
                facecolor='black',
                alpha=config["layout"]["background_alpha"],
                edgecolor='none'
            )
            ax.add_patch(rounded_box)

            # Add table text with LaTeX formatting if available
            logger.debug("Rendering event text on calendar")
            # Start text positioning from the top of the box (fixed position)
            y_offset = box_top_y - padding - 20
            for i, (time_str, title, color) in enumerate(table_rows):
                text_color = color
                logger.debug(f"  Row {i+1}: {time_str} | {title[:20]}{'...' if len(title) > 20 else ''} | {color}")

                # Format text with LaTeX if enabled
                if plt.rcParams['text.usetex']:
                    # LaTeX formatting for better typography
                    time_text = rf'\textbf{{{time_str}}}'
                    title_text = rf'{title.replace("&", r"\&").replace("#", r"\#")}'
                else:
                    time_text = time_str
                    title_text = title

                # Time column (left) - bold formatting
                ax.text(box_x + 20, y_offset, time_text,
                       fontsize=config["text"]["font_size"], color=text_color, weight='bold',
                       verticalalignment='center')

                # Title column (right)
                ax.text(box_x + 150, y_offset, title_text,
                       fontsize=config["text"]["font_size"], color=text_color,
                       verticalalignment='center')

                y_offset -= line_height

    # Save the figure with exact dimensions
    output_path = output_filename
    logger.info(f"Saving lockscreen image to: {output_path}")
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    plt.savefig(output_path, bbox_inches=None, pad_inches=0, dpi=100, facecolor='none')
    plt.close()
    logger.debug("Image saved and matplotlib figure closed")

    return output_path


def upload_to_s3(lockscreen_image, image_name="lockscreen.jpg"):
    """
    Upload lockscreen image to AWS S3 bucket

    Args:
        lockscreen_image (str): Path to the local image file
        image_name (str): Name to use for the uploaded file in S3

    Returns:
        bool: True if upload successful, False otherwise
    """
    logger.info(f"Uploading {lockscreen_image} to S3 bucket: {AWS_BUCKET_NAME}")
    logger.debug(f"Upload parameters - Image: {image_name}, Path: {lockscreen_image}")

    try:
        # Check if file exists
        if not os.path.exists(lockscreen_image):
            logger.error(f"File not found: {lockscreen_image}")
            return False

        # Create S3 client
        logger.debug("Creating S3 client")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        # Upload file
        logger.debug(f"Starting upload to s3://{AWS_BUCKET_NAME}/{image_name}")
        s3_client.upload_file(
            Filename=lockscreen_image,
            Bucket=AWS_BUCKET_NAME,
            Key=image_name,
            ExtraArgs={
                'ContentType': 'image/jpeg',
                'ACL': 'public-read',  # Make the image publicly accessible
                'CacheControl': 'max-age=60'  # Set cache control for 60 seconds
            }
        )

        # Generate public URL
        public_url = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{image_name}"
        logger.success(f"Successfully uploaded to S3: {public_url}")
        return True

    except NoCredentialsError:
        logger.error("AWS credentials not found. Please check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"S3 bucket '{AWS_BUCKET_NAME}' does not exist")
        elif error_code == 'AccessDenied':
            logger.error("Access denied. Please check your AWS credentials and bucket permissions")
        else:
            logger.error(f"AWS S3 error ({error_code}): {e.response['Error']['Message']}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}")
        return False






# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
