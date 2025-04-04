import requests
from bs4 import BeautifulSoup
import datetime
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import re
from dateutil import parser
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from io import BytesIO
import threading
import concurrent.futures

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Define paths relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, "credentials.json")
TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.pickle")

def get_calendar_service():
    """Set up and return Google Calendar service with calendar ID from credentials"""
    creds = None
    calendar_id = None
    
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"ERROR: Could not find credentials file at {CREDENTIALS_PATH}")
                print(f"Current working directory is: {os.getcwd()}")
                raise FileNotFoundError(f"credentials.json not found at {CREDENTIALS_PATH}")
            
            # Load the credentials.json file to get the calendar_id
            with open(CREDENTIALS_PATH, 'r') as f:
                creds_data = json.load(f)
                if 'calendar_id' in creds_data:
                    calendar_id = creds_data['calendar_id']
                else:
                    raise ValueError("calendar_id not found in credentials.json")
                
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    # If we don't have calendar_id yet, load it from credentials.json
    if not calendar_id:
        with open(CREDENTIALS_PATH, 'r') as f:
            creds_data = json.load(f)
            if 'calendar_id' in creds_data:
                calendar_id = creds_data['calendar_id']
            else:
                raise ValueError("calendar_id not found in credentials.json")
    
    service = build('calendar', 'v3', credentials=creds)
    return service, calendar_id

def get_detailed_event_info(event_url, headers, event_data):
    """Extract detailed start and end times from event's detail page"""
    try:
        response = requests.get(event_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch detailed page for {event_data.get('title')}: {response.status_code}")
            return event_data
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for start and end times on the detailed page
        start_label = soup.find(string=lambda text: text and "start" in text.lower())
        end_label = soup.find(string=lambda text: text and "end" in text.lower())
        
        # Extract bonus information for Spotlight events
        if event_data.get('event_type') == "Spotlight":
            # First try to find the exact pattern from your example
            all_paragraphs = soup.find_all('p')
            bonus_info = None
            
            # Debug: Print the paragraphs to see their content
            for i, paragraph in enumerate(all_paragraphs):
                text = paragraph.get_text().strip()
                print(f"Paragraph {i}: {text}")
                
                # Look specifically for the pattern from your example
                if "special bonus is" in text.lower():
                    # Find the position of "special bonus is"
                    start_pos = text.lower().find("special bonus is")
                    # Extract everything after "special bonus is"
                    raw_bonus = text[start_pos + len("special bonus is"):].strip()
                    # Clean up any markdown or extra characters
                    bonus_info = raw_bonus.replace("**", "").strip()
                    print(f"Found bonus text: {bonus_info}")
                    break
            
            # If we don't find the exact pattern, try other common patterns
            if not bonus_info:
                patterns = [
                    r"special bonus is\s*(?:\*\*)?(.*?)(?:\*\*)?(?:\.|\s|$)",
                    r"bonus is\s*(?:\*\*)?(.*?)(?:\*\*)?(?:\.|\s|$)",
                    r"bonus:\s*(?:\*\*)?(.*?)(?:\*\*)?(?:\.|\s|$)",
                    r"(\d+[×x].+?(?:Candy|XP|Stardust|Dust))",
                    r"double\s+(.+?(?:Candy|XP|Stardust|Dust))",
                ]
                
                for paragraph in all_paragraphs:
                    text = paragraph.get_text().strip()
                    for pattern in patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            bonus_info = match.group(1).strip()
                            print(f"Matched with pattern '{pattern}': {bonus_info}")
                            break
                    if bonus_info:
                        break
            
            if bonus_info:
                event_data['bonus'] = bonus_info
                print(f"Found bonus for {event_data.get('title')}: {bonus_info}")
        
        # Function to clean date strings
        def clean_date_string(date_str):
            if not date_str:
                return None
                
            # Clean up extra spaces and remove "Local Time"
            date_str = re.sub(r'\s+', ' ', date_str).strip()
            date_str = date_str.replace(" Local Time", "")
            
            # Extract the date components with regex
            pattern = r'(\w+), (\w+ \d+, \d+),? at (\d+:\d+ [AP]M)'
            match = re.match(pattern, date_str)
            
            if match:
                weekday, date_part, time_part = match.groups()
                clean_str = f"{date_part} {time_part}"
                try:
                    parsed_date = datetime.datetime.strptime(clean_str, "%B %d, %Y %I:%M %p")
                    return parsed_date
                except ValueError:
                    print(f"Failed to parse cleaned date string: {clean_str}")
            
            return None
        
        # Extract start time
        if start_label and start_label.find_next():
            start_time_text = start_label.find_next().get_text().strip()
            parsed_start = clean_date_string(start_time_text)
            if parsed_start:
                event_data['detailed_start_time'] = parsed_start
                print(f"Found detailed start time for {event_data.get('title')}: {parsed_start}")
        
        # Extract end time
        if end_label and end_label.find_next():
            end_time_text = end_label.find_next().get_text().strip()
            parsed_end = clean_date_string(end_time_text)
            if parsed_end:
                event_data['detailed_end_time'] = parsed_end
                print(f"Found detailed end time for {event_data.get('title')}: {parsed_end}")
        
        # If we found both detailed times, use them instead of the main page times
        if event_data.get('detailed_start_time') and event_data.get('detailed_end_time'):
            event_data['start_time'] = event_data['detailed_start_time']
            event_data['end_time'] = event_data['detailed_end_time']
            event_data['is_multi_day'] = (event_data['end_time'].date() > event_data['start_time'].date())
            
            # Update display strings
            event_data['display_start'] = event_data['start_time'].strftime('%b %d, %Y')
            event_data['display_end'] = event_data['end_time'].strftime('%b %d, %Y') if event_data['is_multi_day'] else None
            event_data['display_start_time'] = event_data['start_time'].strftime('%I:%M %p')
            event_data['display_end_time'] = event_data['end_time'].strftime('%I:%M %p')
        
        # Try to extract a better description if available
        description_elem = soup.find("div", class_="event-description")
        if description_elem:
            event_data['description'] = description_elem.get_text().strip()
        
    except Exception as e:
        print(f"Error fetching detailed page for {event_data.get('title')}: {str(e)}")
    
    return event_data

def scrape_leekduck_events():
    """Scrape events from LeekDuck website with improved time parsing"""
    url = "https://leekduck.com/events/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Response status code: {response.status_code}")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        
        # Find all event items
        event_items = []
        
        # Try to find event sections first
        event_sections = soup.find_all('div', class_=lambda c: c and ('event' in c.lower() or 'raids' in c.lower()))
        print(f"Found {len(event_sections)} potential event sections")
        
        # If we found sections, extract events from them
        if event_sections:
            for section in event_sections:
                items = section.find_all('a', href=True)
                event_items.extend(items)
        
        # If no luck with sections, try finding events directly
        if not event_items:
            event_items = soup.find_all('a', href=lambda h: h and '/events/' in h)
            print(f"Found {len(event_items)} events with link-based search")
        
        # If still no luck, try a very broad approach
        if not event_items:
            event_items = soup.find_all(['div', 'a'], class_=lambda c: c and ('item' in c.lower() or 'event' in c.lower() or 'raid' in c.lower()))
            print(f"Found {len(event_items)} events with broad class search")

        print(f"Total event items found: {len(event_items)}")
        
        # Track processed event titles to avoid duplicates
        processed_events = set()
        
        # Process each event
        for i, item in enumerate(event_items):
            event_data = {}
            
            # Extract the event link first to use later for detailed info
            if 'href' in item.attrs:
                event_link = item['href']
                # Make sure URL is absolute
                if not event_link.startswith('http'):
                    event_link = 'https://leekduck.com' + event_link
                event_data['event_link'] = event_link
            
            # Try to extract the title
            title_elem = item.find(['h2', 'h3', 'h4', 'strong', 'span'], class_=lambda c: not c or 'title' in c.lower())
            if title_elem:
                event_data['title'] = title_elem.text.strip()
            else:
                # If no specific title element, use any prominent text
                bold_text = item.find(['b', 'strong'])
                if bold_text:
                    event_data['title'] = bold_text.text.strip()
                else:
                    # If still no title, use the alt text of the image if available
                    img = item.find('img')
                    if img and img.get('alt'):
                        event_data['title'] = img.get('alt').strip()
                    else:
                        # Last resort: use any text content
                        event_data['title'] = item.get_text().strip().split('\n')[0]
            
            # Skip if no title found or title is too generic
            if not event_data.get('title') or len(event_data.get('title', '')) < 3:
                continue
            
            # Skip duplicate events (by title)
            if event_data.get('title') in processed_events:
                continue
                
            processed_events.add(event_data.get('title'))
            print(f"Found event: {event_data.get('title')}")
            
            # Store the original index
            event_data['original_index'] = i
            
            # Determine event type for categorization
            event_type = "General"
            title_lower = event_data.get('title', '').lower()
            
            # Event type categorization
            if "raid" in title_lower or "raids" in title_lower:
                event_type = "Raid"
            elif "community day" in title_lower:
                event_type = "Community Day"
            elif "spotlight" in title_lower:
                event_type = "Spotlight"
            elif "battle" in title_lower or "league" in title_lower:
                event_type = "Battle"
            elif "hatch" in title_lower:
                event_type = "Hatch Day"
            elif "mega" in title_lower:
                event_type = "Mega"
            elif "power up ticket" in title_lower or "ticket" in title_lower:
                event_type = "Ticket"
            elif "shadow" in title_lower:
                event_type = "Shadow"
            
            event_data['event_type'] = event_type
            
            # Check for event category/type from the parent element
            parent_type = None
            parent = item.parent
            if parent:
                parent_class = parent.get('class', [])
                for cls in parent_class:
                    if 'raid' in cls.lower():
                        parent_type = "Raid"
                    elif 'battle' in cls.lower():
                        parent_type = "Battle"
            
            if parent_type and event_type == "General":
                event_data['event_type'] = parent_type
            
            # Try to extract date information
            date_text = ""
            # Look for date text patterns
            for text in item.stripped_strings:
                if re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', text):
                    date_text = text
                    break
            
            if date_text:
                event_data['date_text'] = date_text
                print(f"Event date text: {date_text}")
                
                # Preliminary time parsing from main page (may be incomplete)
                try:
                    # Check for basic date and time patterns
                    date_pattern = r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,\s+\d{4})?)'
                    time_pattern = r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))'
                    
                    date_match = re.search(date_pattern, date_text)
                    time_match = re.search(time_pattern, date_text)
                    
                    if date_match and time_match:
                        date_str = date_match.group(1)
                        time_str = time_match.group(1)
                        
                        # Default parsing attempt from main page
                        try:
                            datetime_str = f"{date_str} {time_str}"
                            parsed_datetime = parser.parse(datetime_str)
                            
                            # For now, set start and end time the same since we'll update it later
                            event_data['start_time'] = parsed_datetime
                            event_data['end_time'] = parsed_datetime + datetime.timedelta(hours=1)
                            event_data['is_multi_day'] = False
                            
                            event_data['display_start'] = parsed_datetime.strftime('%b %d, %Y')
                            event_data['display_start_time'] = parsed_datetime.strftime('%I:%M %p')
                            event_data['display_end_time'] = (parsed_datetime + datetime.timedelta(hours=1)).strftime('%I:%M %p')
                        except Exception as inner_e:
                            print(f"Error parsing datetime '{datetime_str}': {str(inner_e)}")
                except Exception as e:
                    print(f"Error in basic time parsing for '{event_data.get('title')}': {str(e)}")
            
            # Extract image
            img_elem = item.find('img')
            if img_elem and img_elem.get('src'):
                image_url = img_elem['src']
                # Make sure URL is absolute
                if not image_url.startswith('http'):
                    image_url = 'https://leekduck.com' + image_url
                event_data['image_url'] = image_url
            
            # Initial extraction is complete, add the event to our list
            if event_data.get('title') and event_data.get('event_link'):
                events.append(event_data)
        
        # Now fetch detailed info for each event
        print("Fetching detailed information for each event...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit tasks to the executor
            future_to_event = {
                executor.submit(get_detailed_event_info, event['event_link'], headers, event): i 
                for i, event in enumerate(events) if 'event_link' in event
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_event):
                event_idx = future_to_event[future]
                try:
                    updated_event = future.result()
                    events[event_idx] = updated_event
                except Exception as e:
                    print(f"Error processing event {events[event_idx].get('title')}: {str(e)}")
        
        print(f"Completed scraping {len(events)} events with detailed information.")
        return events
        
    except Exception as e:
        print(f"Error scraping LeekDuck: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def create_calendar_events_direct(selected_events):
    """Create Google Calendar events from direct event objects"""
    if not selected_events:
        print("No events to add to calendar")
        return []
        
    created_events = []
    try:
        service, calendar_id = get_calendar_service()
        
        # Get existing events to avoid duplicates
        existing_events = get_existing_events(service, calendar_id)
        
        for event in selected_events:
            # Skip events with unparseable dates
            if not event.get('start_time') or not event.get('end_time'):
                print(f"Skipping event with unparseable dates: {event.get('title')}")
                continue
            
            # Check if event already exists - using both title and start time
            event_exists = False
            event_start_iso = event.get('start_time').isoformat()
            
            for existing in existing_events:
                existing_start = None
                if existing.get('start', {}).get('dateTime'):
                    existing_start = existing.get('start', {}).get('dateTime')
                elif existing.get('start', {}).get('date'):
                    # For all-day events
                    existing_start = existing.get('start', {}).get('date') + "T00:00:00"
                
                if (existing.get('summary') == event.get('title') and 
                    existing_start and event_start_iso.startswith(existing_start[:16])):
                    event_exists = True
                    break
            
            if event_exists:
                print(f"Event already exists: {event.get('title')}")
                continue
            
            # Create event
            event_link = event.get('event_link', 'https://leekduck.com/events/')
            
            # Determine if this is a multi-day event and if it should be all-day
            is_multi_day = event.get('is_multi_day', False)
            
            # Calculate if this should be an all-day event
            # Criteria: multi-day event with time at or near beginning/end of day
            start_near_day_start = event.get('start_time').hour < 2  # Before 2 AM
            end_near_day_end = event.get('end_time').hour > 21  # After 9 PM
            is_all_day = is_multi_day and start_near_day_start and end_near_day_end
            
            # Check if this is a day-long event (starting early and ending late)
            is_day_long = (
                not is_multi_day and 
                event.get('start_time').hour < 10 and
                event.get('end_time').hour > 18 and
                (event.get('end_time') - event.get('start_time')).seconds > 7 * 3600  # more than 7 hours
            )
            
            # Day-long events should also be treated as all-day
            is_all_day = is_all_day or is_day_long
            
            # Modify the title for Spotlight events to include the bonus
            event_title = event.get('title', 'Unnamed Event')
            if event.get('event_type') == "Spotlight" and event.get('bonus'):
                event_title = f"{event_title} ({event.get('bonus')})"
            
            calendar_event = {
                'summary': event_title,
                'description': (event.get('description', '') or 'Pokémon GO event') + 
                              f"\n\nSource: {event_link}" + 
                              (f"\nImage: {event.get('image_url', '')}" if event.get('image_url') else "") +
                              f"\n\nEvent Type: {event.get('event_type', 'General')}" +
                              (f"\nBonus: {event.get('bonus')}" if event.get('event_type') == "Spotlight" and event.get('bonus') else ""),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            if is_all_day:
                # Use date format for all-day events
                calendar_event['start'] = {
                    'date': event.get('start_time').date().isoformat(),
                }
                # For all-day events, end date should be the day after the last day
                end_date = event.get('end_time').date() + datetime.timedelta(days=1)
                calendar_event['end'] = {
                    'date': end_date.isoformat(),
                }
                print(f"Creating all-day event from {event.get('start_time').date()} to {end_date}")
            else:
                # Use dateTime format for timed events
                calendar_event['start'] = {
                    'dateTime': event.get('start_time').isoformat(),
                    'timeZone': 'America/New_York',
                }
                calendar_event['end'] = {
                    'dateTime': event.get('end_time').isoformat(),
                    'timeZone': 'America/New_York',
                }
            
            # Insert event
            try:
                created_event = service.events().insert(calendarId=calendar_id, body=calendar_event).execute()
                print(f"Event created: {event.get('title')}")
                created_events.append(event.get('title'))
            except Exception as e:
                print(f"Failed to create event {event.get('title')}: {str(e)}")
        
        return created_events
    except Exception as e:
        print(f"Error creating calendar events: {str(e)}")
        return []

def get_existing_events(service, calendar_id):
    """Get existing events from calendar to avoid duplicates"""
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    try:
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now,
            maxResults=2500, singleEvents=True,
            orderBy='startTime').execute()
        return events_result.get('items', [])
    except Exception as e:
        print(f"Error getting existing events: {str(e)}")
        return []

class EventConfirmationUI:
    def __init__(self, root, events):
        self.root = root
        self.events = events
        self.selected_indices = []
        self.var_checkboxes = []
        self.event_frames = []  # Store references to event frames with metadata
        
        # Get all unique event types
        all_event_types = set(event.get('event_type', 'General') for event in events)
        self.event_types = sorted(list(all_event_types))
        
        # Define colors for event types
        self.type_colors = {
            "Raid": "#E57373",        # Light Red
            "Community Day": "#81C784", # Light Green
            "Spotlight": "#64B5F6",    # Light Blue
            "Battle": "#FFB74D",       # Light Orange
            "Hatch Day": "#9575CD",    # Light Purple
            "Mega": "#FF8A65",         # Light Deep Orange
            "General": "#B0BEC5",      # Light Blue Grey
            "Ticket": "#4DB6AC",       # Light Teal
            "Shadow": "#9E9E9E"        # Light Grey
        }
        
        # Configure filter variables
        self.filter_vars = {}
        for event_type in self.event_types:
            self.filter_vars[event_type] = tk.BooleanVar(value=True)
        
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("Pokémon GO Event Calendar - Confirm Events")
        self.root.geometry("1000x700")
        
        # Configure style
        style = ttk.Style()
        style.configure("Card.TFrame", relief="solid", borderwidth=1)
        style.configure("Title.TLabel", font=("Helvetica", 11, "bold"))
        style.configure("Date.TLabel", font=("Helvetica", 9))
        style.configure("Time.TLabel", font=("Helvetica", 9, "bold"))
        style.configure("Type.TLabel", font=("Helvetica", 9), foreground="white")
        style.configure("DateHeader.TLabel", font=("Helvetica", 12, "bold"), foreground="#1976D2")
        style.configure("FilterCheckbutton.TCheckbutton", font=("Helvetica", 9))
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(main_frame, text="Select Events to Add to Calendar", font=("Helvetica", 16, "bold"))
        header.pack(pady=10)
        
        # Top actions frame
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 5))
        
        # Select All Checkbox
        select_all_var = tk.BooleanVar(value=True)  # Default all selected
        select_all_cb = ttk.Checkbutton(
            top_frame, 
            text="Select All", 
            variable=select_all_var,
            command=lambda: self.toggle_all(select_all_var.get())
        )
        select_all_cb.pack(side="left", padx=(0, 20))
        
        # Buttons on right side of top frame
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side="right")
        
        # Cancel button
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.root.destroy)
        cancel_btn.pack(side="left", padx=5)
        
        # Submit button
        submit_btn = ttk.Button(
            btn_frame, 
            text="Add Selected Events to Calendar", 
            command=self.submit,
            style="Accent.TButton"
        )
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        submit_btn.pack(side="left", padx=5)
        
        # Filters labelframe (similar to your screenshot)
        filters_labelframe = ttk.LabelFrame(main_frame, text="Filter by Event Type", padding=(5, 5))
        filters_labelframe.pack(fill="x", pady=(0, 10))
        
        # Create filter grid inside the labelframe
        filters_frame = ttk.Frame(filters_labelframe)
        filters_frame.pack(fill="x", padx=5, pady=5)
        
        # Create filter checkboxes in a horizontal row (like in your screenshot)
        for i, event_type in enumerate(self.event_types):
            color = self.type_colors.get(event_type, "#B0BEC5")
            
            # Create a frame for the filter
            filter_item = ttk.Frame(filters_frame)
            filter_item.grid(row=0, column=i, padx=10, pady=2, sticky="w")
            
            # Add color indicator
            color_indicator = tk.Frame(filter_item, background=color, width=15, height=15)
            color_indicator.pack(side="left", padx=(0, 5))
            
            # Add checkbox
            cb = ttk.Checkbutton(
                filter_item, 
                text=event_type, 
                variable=self.filter_vars[event_type],
                style="FilterCheckbutton.TCheckbutton",
                command=self.apply_filters
            )
            cb.pack(side="left")
        
        # Create scrollable frame for events
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Add events to scrollable frame
        self.display_events()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def display_events(self):
        """Display events in the scrollable frame with improved formatting"""
        # Sort events by date
        sorted_events = sorted(self.events, key=lambda e: e.get('start_time') if e.get('start_time') else datetime.datetime.max)
        
        # Group events by date
        date_groups = {}
        for event in sorted_events:
            if event.get('start_time'):
                date_key = event['start_time'].strftime('%Y-%m-%d')
                if date_key not in date_groups:
                    date_groups[date_key] = []
                date_groups[date_key].append(event)
        
        # Store frame references for each date section
        self.date_frames = {}
        
        # Clear existing event frames list
        self.event_frames = []
        self.var_checkboxes = []
        
        # Display events grouped by date
        for date_key in sorted(date_groups.keys()):
            # Create date header with more readable format
            sample_date = date_groups[date_key][0]['start_time']
            date_str = sample_date.strftime('%A, %B %d, %Y')
            date_frame = ttk.Frame(self.scrollable_frame)
            date_frame.pack(fill="x", pady=(10, 0))
            self.date_frames[date_key] = date_frame
            
            date_header = ttk.Label(
                date_frame, 
                text=date_str,
                style="DateHeader.TLabel"
            )
            date_header.pack(fill="x", padx=5, pady=(5, 3), anchor="w")
            
            # Add separator after date header
            ttk.Separator(date_frame, orient="horizontal").pack(fill="x", padx=5, pady=(0, 5))
            
            # Create a frame for the events in this date
            events_frame = ttk.Frame(date_frame)
            events_frame.pack(fill="x", padx=5, pady=5)
            
            # Display events for this date in a single column as in your screenshot
            for event in date_groups[date_key]:
                # Create event card
                event_frame = self.create_event_card(events_frame, event)
                event_frame.pack(fill="x", padx=5, pady=5)
    
    def create_event_card(self, parent, event):
        event_frame = ttk.Frame(parent, padding=(0, 0, 0, 0), style="Card.TFrame")
        
        # Store reference to event frame with metadata AND the actual event object
        frame_data = {
            'frame': event_frame,
            'type': event.get('event_type', 'General'),
            'date_key': event['start_time'].strftime('%Y-%m-%d') if event.get('start_time') else None,
            'original_index': event.get('original_index'),
            'event_object': event  # Store direct reference to the event object itself
        }
        self.event_frames.append(frame_data)
        
        # Configure background color based on event type
        bg_color = self.type_colors.get(event.get('event_type', 'General'), "#B0BEC5")
        
        # Create type indicator (left vertical bar)
        type_frame = tk.Frame(event_frame, background=bg_color, width=5)
        type_frame.pack(side="left", fill="y")
        
        # Create content frame
        content_frame = ttk.Frame(event_frame, padding=(10, 5))
        content_frame.pack(side="left", fill="both", expand=True)
        
        # Create checkbox with the frame data attached
        var_cb = tk.BooleanVar(value=True)
        var_cb.frame_data = frame_data  # Store direct reference to frame data
        self.var_checkboxes.append(var_cb)
        
        # Checkbox and Title row
        top_row = ttk.Frame(content_frame)
        top_row.pack(fill="x", anchor="w")
        
        cb = ttk.Checkbutton(
            top_row, 
            variable=var_cb
        )
        cb.pack(side="left", anchor="nw")
        
        # Title - Add bonus in parentheses for Spotlight events
        title_text = event.get('title', 'Unnamed Event')
        if event.get('event_type') == "Spotlight" and event.get('bonus'):
            title_text = f"{title_text} ({event.get('bonus')})"
        
        title = ttk.Label(
            top_row,
            text=title_text,
            style="Title.TLabel",
            wraplength=800
        )
        title.pack(side="left", anchor="nw", fill="x", expand=True)
        
        # Information rows
        info_frame = ttk.Frame(content_frame)
        info_frame.pack(fill="x", anchor="w")
        
        # Date row
        if event.get('start_time'):
            date_label = ttk.Label(
                info_frame,
                text=f"Date: {event['display_start']}",
                style="Date.TLabel"
            )
            date_label.grid(row=0, column=0, sticky="w", padx=(18, 0))  # Align with checkbox
        
        # Time row with proper format for multi-day events
        if event.get('start_time') and event.get('end_time'):
            if event.get('is_multi_day', False):
                # Format for multi-day events - show full dates with times
                start_str = event['start_time'].strftime('%b %d, %Y at %I:%M %p')
                end_str = event['end_time'].strftime('%b %d, %Y at %I:%M %p')
                time_text = f"Time: {start_str} to {end_str}"
            else:
                # Format for same-day events - just show the times
                start_str = event['start_time'].strftime('%I:%M %p')
                end_str = event['end_time'].strftime('%I:%M %p')
                time_text = f"Time: {start_str} to {end_str}"
                
            time_label = ttk.Label(
                info_frame,
                text=time_text,
                style="Time.TLabel"
            )
            time_label.grid(row=1, column=0, sticky="w", padx=(18, 0))
        
        # Type row
        type_label = ttk.Label(
            info_frame,
            text=f"Type: {event.get('event_type', 'General')}",
            style="Date.TLabel"
        )
        type_label.grid(row=2, column=0, sticky="w", padx=(18, 0))
        
        # Add Bonus row for Spotlight events
        if event.get('event_type') == "Spotlight" and event.get('bonus'):
            bonus_label = ttk.Label(
                info_frame,
                text=f"Bonus: {event.get('bonus')}",
                style="Date.TLabel"
            )
            bonus_label.grid(row=3, column=0, sticky="w", padx=(18, 0))
        
        return event_frame
    
    def toggle_all(self, state):
        for var in self.var_checkboxes:
            var.set(state)
    
    def apply_filters(self):
        """Apply filters to show/hide events based on selected types"""
        for item in self.event_frames:
            event_type = item['type']
            frame = item['frame']
            date_key = item['date_key']
            
            if self.filter_vars.get(event_type, tk.BooleanVar(value=True)).get():
                frame.pack()  # Show the event
            else:
                frame.pack_forget()  # Hide the event
        
        # Show/hide date headers if all their events are hidden
        for date_key, date_frame in self.date_frames.items():
            # Check if any visible events remain for this date
            visible_events = False
            for item in self.event_frames:
                if item['date_key'] == date_key and self.filter_vars.get(item['type'], tk.BooleanVar(value=True)).get():
                    visible_events = True
                    break
            
            if visible_events:
                date_frame.pack(fill="x", pady=(10, 0))  # Show the date section
            else:
                date_frame.pack_forget()  # Hide the date section
    
    def submit(self):
        # Get selected events directly
        selected_events = []
        
        for var in self.var_checkboxes:
            if var.get():
                event_type = var.frame_data['type']
                # Only include visible (filtered in) events
                if self.filter_vars.get(event_type, tk.BooleanVar(value=True)).get():
                    selected_events.append(var.frame_data['event_object'])
        
        if not selected_events:
            messagebox.showwarning("No Events Selected", "Please select at least one event to add to calendar.")
            return
        
        # Create the events in Google Calendar - using the actual event objects
        created_events = create_calendar_events_direct(selected_events)
        
        if created_events:
            messagebox.showinfo(
                "Events Added", 
                f"Successfully added {len(created_events)} events to the calendar:\n\n" + 
                "\n".join([f"• {event}" for event in created_events])
            )
        else:
            messagebox.showinfo("No Events Added", "No new events were added to the calendar.")
        
        self.root.destroy()

def main():
    """Main function to run the script"""
    print("Scraping events from LeekDuck...")
    
    events = scrape_leekduck_events()
    print(f"Found {len(events)} events")
    
    if not events:
        print("No events found. Exiting.")
        return
    
    # Launch Tkinter UI for event confirmation
    root = tk.Tk()
    
    # Configure the style
    style = ttk.Style()
    style.configure("Card.TFrame", relief="solid", borderwidth=1)
    
    app = EventConfirmationUI(root, events)
    root.mainloop()

if __name__ == "__main__":
    main()
