# Pokémon GO Event Calendar

A Python application that scrapes upcoming Pokémon GO events from LeekDuck.com and adds them to your Google Calendar, with smart detection of updates and changes to existing events.

![App Screenshot](https://snapshotsdingpc.s3.us-east-1.amazonaws.com/PogoCal.JPG)

## Features

- Scrapes event information from LeekDuck.com including:
  - Event title, date, and time
  - Event type (Raid, Community Day, Spotlight, etc.)
  - Special bonuses for Spotlight events
  - Multi-day event support
- Clean UI for selecting which events to add
- Color-coded event types for easy filtering
- Smart update detection:
  - Avoids duplicate events
  - Detects when an event has been updated with new information
  - Asks for confirmation before replacing outdated events
- Configurable through a JSON file

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/pokemon-go-calendar.git
cd pokemon-go-calendar
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Create and configure your Google API credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API
   - Create OAuth 2.0 Client ID credentials
   - Download the credentials.json file and place it in the project directory

4. Create a configuration file:
```
python pogocal.py --create-config
```

5. Edit the generated config.json file with your Google Calendar ID and other settings

## Usage

### Basic Usage

Run the application:
```
python pogocal.py
```

This will:
1. Scrape upcoming events from LeekDuck.com
2. Display a UI to select which events to add
3. Add the selected events to your Google Calendar

### Command Line Options

- `--force-auth`: Force re-authentication with Google (useful if your token has expired)
- `--create-config`: Create a default config.json file

### Configuration

The config.json file contains the following sections:

```json
{
    "google_api": {
        "credentials_path": "credentials.json",
        "calendar_id": "your_calendar_id_here@group.calendar.google.com"
    },
    "leekduck": {
        "url": "https://leekduck.com/events/",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    },
    "app": {
        "window_size": "1000x700",
        "default_reminders": [
            {"method": "popup", "minutes": 60},
            {"method": "popup", "minutes": 10}
        ],
        "timezone": "America/New_York"
    },
    "event_colors": {
        "Raid": "#E57373",
        "Community Day": "#81C784",
        "Spotlight": "#64B5F6",
        // ...more event types and colors
    }
}
```

## How to Find Your Google Calendar ID

1. Open [Google Calendar](https://calendar.google.com/)
2. Click on the three dots next to the calendar you want to use
3. Select "Settings and sharing"
4. Scroll down to "Integrate calendar"
5. Copy the "Calendar ID" value

## Security & Privacy

- Your Google API credentials are stored locally in the credentials.json file
- Authentication tokens are stored in token.pickle
- No data is sent to any servers other than Google and LeekDuck.com
- Add both credentials.json and token.pickle to your .gitignore file if you're pushing to a public repository

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [LeekDuck.com](https://leekduck.com/) for providing reliable Pokémon GO event information
- Pokémon GO players everywhere who want to stay on top of events

## Disclaimer

This project is not affiliated with Niantic, The Pokémon Company, or LeekDuck. Pokémon GO is a trademark of Niantic, Inc.
