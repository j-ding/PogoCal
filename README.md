# Pokémon GO Event Calendar

A Python application that automatically scrapes upcoming Pokémon GO events from LeekDuck.com and adds them to your Google Calendar with just a few clicks.

![App Screenshot]((https://snapshotsdingpc.s3.us-east-1.amazonaws.com/PogoCal.JPG))

## Features

- Scrapes current and upcoming Pokémon GO events directly from LeekDuck.com
- Categorizes events by type (Raids, Community Days, Spotlight Hours, etc.)
- Visual filtering interface to select which events to add
- Color-coded event display by category
- Automatically formats times appropriately for single-day and multi-day events
- Adds detailed event information to Google Calendar, including links to the original event page
- Special handling for Spotlight Hours to display the bonus information (e.g., "2× Transfer Candy")
- Avoids duplicate event creation

## Requirements

- Python 3.7+
- Google account with Calendar access
- The following Python packages:
  - requests
  - beautifulsoup4
  - google-auth
  - google-auth-oauthlib
  - google-api-python-client
  - python-dateutil
  - Pillow
  - tkinter (usually comes with Python)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/pokemon-go-event-calendar.git
   cd pokemon-go-event-calendar
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Calendar API credentials:
   - Visit the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API for your project
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials as JSON

4. Create a `credentials.json` file in the root directory of the project with the following structure:
   ```json
   {
     "installed": {
       "client_id": "your-client-id",
       "project_id": "your-project-id",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_secret": "your-client-secret",
       "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
     },
     "calendar_id": "your-calendar-id@group.calendar.google.com"
   }
   ```
   
   Note: To get your calendar ID, go to your Google Calendar settings, select the calendar you want to use, and scroll down to "Integrate calendar" section.

## Usage

1. Run the application:
   ```bash
   python pogoCal.py
   ```

2. The application will:
   - Scrape current and upcoming events from LeekDuck
   - Display a UI with all events organized by date
   - Allow you to select which events to add to your calendar

3. Use the filter checkboxes to show/hide specific event types

4. Check/uncheck individual events as needed

5. Click "Add Selected Events to Calendar" to add the events to your Google Calendar

6. The first time you run the app, it will open a browser window for Google OAuth authentication. Grant the requested permissions to allow the app to access your calendar.

## How It Works

The application uses:

1. **Web Scraping**: Uses BeautifulSoup to extract event information from LeekDuck.com
2. **Data Processing**: Parses dates, times, and event details
3. **Tkinter UI**: Provides a user-friendly interface for selecting events
4. **Google Calendar API**: Interfaces with Google Calendar to add events

Events are scraped from the main events page and then each individual event page is visited to gather detailed information like precise start/end times and special bonus information for Spotlight Hours.

## Future Enhancements

- Auto-update existing events when details change
- Scheduled automatic running
- Notification options
- More filtering capabilities
- Dark mode UI

## License

[MIT License](LICENSE)

## Acknowledgments

- [LeekDuck.com](https://leekduck.com/) for providing comprehensive Pokémon GO event information
- Google Calendar API for calendar integration capabilities
