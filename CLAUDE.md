# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an iPhone lockscreen calendar generator that creates custom wallpapers by combining calendar events with background images and uploading them to AWS S3.

## Core Architecture

The application follows a simple pipeline architecture in `main.py`:
1. **Event Collection** (`get_todays_events()`) - Fetches today's events from multiple iCal feeds
2. **Background Selection** (`pick_random_background()`) - Randomly selects and crops background images
3. **Image Generation** (`generate_lockscreen_image()`) - Overlays calendar events on background
4. **Upload** (`upload_to_s3()`) - Uploads final image to S3 bucket

## Key Configuration

Configuration is managed through `inputs/config.toml` which contains:

- **Display Dimensions**: iPhone screen dimensions (1290x2796 pixels)
- **Calendar Sources**: Multiple iCal feeds with custom colors:
  - Personal Google Calendar
  - KBR Google Calendar
  - Org Home calendar from Dropbox
  - Org Work calendar from Dropbox
  - Birthdays calendar
- **Background Images**: Stored in `inputs/backgrounds/` directory (PNG format)
- **AWS Configuration**: S3 bucket and credentials for image upload
- **Layout Settings**: Box positioning, fonts, colors, and transparency
- **Timezone**: Australia/Brisbane for local time display
- **Behavior**: Past event thresholds, text truncation, logging levels

## Environment Management

This project uses `uv` for Python environment management. The virtual environment is located at `C:\Users\Chris\venv\iphone_lockscreen_calendar` (external to the project directory).

**Important**: Always use `uv run --active` to target the correct virtual environment instead of the local `.venv`.

## Running the Application

```bash
uv run --active python main.py
```

## Adding Dependencies

```bash
uv add --active package_name
```

## Future Deployment

The project will eventually need a Dockerfile and Docker image for deployment.

## Development Notes

- All core functions are currently stub implementations that need to be completed
- The project will require dependencies for:
  - iCal parsing (likely `icalendar`)
  - Image processing (likely `Pillow/PIL`)
  - AWS S3 integration (`boto3`)
  - Calendar/date handling (`pandas`, `datetime`)
- Background images are pre-cropped PNG files in the inputs directory
- Each calendar feed has an associated text color for visual differentiation

## File Structure

```
main.py              # Core application logic
inputs/
  config.toml        # Configuration file with all settings
  backgrounds/       # Background images (PNG format)
```

The project currently has no dependency management files (requirements.txt, pyproject.toml, etc.) and no existing documentation.