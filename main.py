import requests.auth
import SECRETS
import requests
from colorama import Fore
import time
import threading
import base64
import RPi.GPIO as GPIO

ACCESS_TOKEN = None
REFRESH_TOKEN = None

SKIP_COUNTER = 0
CURRENT_VETO_SONG_ID = 0

SKIPS_IN_FIRST_10_SECONDS = 0

VETOS_PER_PASSENGER = 20

class Passenger:
    def __init__(self, veto_counter: int):
        self.veto_counter = veto_counter
        self.gpio_pins = 0
        self.last_song_skipped = "0"
    
    def skip(self):
        global SKIP_COUNTER
        global SKIPS_IN_FIRST_10_SECONDS

        current_song = get_current_playing_track(ACCESS_TOKEN)

        if current_song["item"]["id"] == CURRENT_VETO_SONG_ID:
            print("Song is protected by veto")
            return

        if current_song["item"]["id"] != self.last_song_skipped:
            self.last_song_skipped = current_song["item"]["id"]

            if current_song["progress_ms"] < 10000:
                SKIPS_IN_FIRST_10_SECONDS += 1

                if SKIPS_IN_FIRST_10_SECONDS == 2:
                    print("Skipping song...")
                    skip_track(ACCESS_TOKEN)
                    SKIP_COUNTER = 0
                    SKIPS_IN_FIRST_10_SECONDS = 0

            SKIP_COUNTER += 1
            print(f"Skip counter for current song {SKIP_COUNTER}/4")

            if SKIP_COUNTER > 2:
                skip_track(ACCESS_TOKEN)
                SKIP_COUNTER = 0
                SKIPS_IN_FIRST_10_SECONDS = 0
        else:
            print("Song was already skipped")
    
    def veto(self):
        global SKIP_COUNTER
        global CURRENT_VETO_SONG_ID

        SKIP_COUNTER = 0
        if self.veto_counter > 0:
            print("Song is now protected by veto...")
            self.veto_counter -= 1
            CURRENT_VETO_SONG_ID = get_current_playing_track(ACCESS_TOKEN)["item"]["id"]

def get_current_playing_track(access_token: str) -> dict:
    # Spotify endpoint for the currently playing track
    current_playing_endpoint = "https://api.spotify.com/v1/me/player/currently-playing"
    
    # Headers with the Bearer token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        # Make a GET request to the endpoint
        response = requests.get(current_playing_endpoint, headers=headers)
        
        # If no content (204 status), return None
        if response.status_code == 204:
            print("No track is currently playing.")
            return None
        
        # Raise an HTTPError for bad responses (4xx and 5xx)
        response.raise_for_status()
        
        # Parse and return the JSON response
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error while retrieving current playing track: {e}")
        return None

def skip_track(access_token: str) -> None:
    # Spotify endpoint for the currently playing track
    skip_track_endpoint = "https://api.spotify.com/v1/me/player/next"
    
    # Headers with the Bearer token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        # Make a GET request to the endpoint
        response = requests.post(skip_track_endpoint, headers=headers)
        
        # Raise an HTTPError for bad responses (4xx and 5xx)
        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        print(f"Error while skipping track: {e}")
        return None

def print_Help() -> str:
    return """
Todo
"""

def construct_Login_Url() -> str:
    encoded_redirect_uri = SECRETS.REDIRECT_URI.replace("/", f"%2F")

    return f"https://accounts.spotify.com/authorize?client_id={SECRETS.SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={encoded_redirect_uri}&scope=user-read-currently-playing%20user-modify-playback-state"

def get_Initial_Access_And_Refresh_Token() -> dict:
    authorization_code = input("Authorization Code: ")

    token_endpoint = "https://accounts.spotify.com/api/token"

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": SECRETS.REDIRECT_URI,
        "client_id": SECRETS.SPOTIFY_CLIENT_ID,
        "client_secret": SECRETS.SPOTIFY_CLIENT_SECRET
    }
    
    try:
        # Make a GET request to the endpoint
        response = requests.post(token_endpoint, data=data)

        if response.status_code == 400:
            print(Fore.RED + "\nAuthorization code is to old, please request a new one and repeat this step.")

        if response.status_code == 200:
            return response.json()
        
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error while retrieving initial access token: {e}")
        return None

def refresh_Access_Token() -> None:
    global ACCESS_TOKEN
    global REFRESH_TOKEN

    refresh_endpoint = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{SECRETS.SPOTIFY_CLIENT_ID}:{SECRETS.SPOTIFY_CLIENT_SECRET}".encode()).decode()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f"Basic {auth_header}",
        "Cache-Control": "no-cache"
    }

    while True:
        time.sleep(3300)

        print(f"Refreshing Token with {REFRESH_TOKEN}")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
        }

        try:
            response = requests.post(refresh_endpoint, data=data, headers=headers)

            response.raise_for_status()

            if response.status_code == 200:
                ACCESS_TOKEN = response.json()['access_token']
                #REFRESH_TOKEN = response.json().refresh_token
                print("New Access Token: " + ACCESS_TOKEN)
                print("New Refresh Token: " + REFRESH_TOKEN)
            
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Error while refreshing access token: {e}")

def start():
    global ACCESS_TOKEN
    global REFRESH_TOKEN

    # =================== HANDLE EXPIRING ACCESS TOKEN ==============================
    initial_access = get_Initial_Access_And_Refresh_Token()

    ACCESS_TOKEN = initial_access['access_token']
    REFRESH_TOKEN = initial_access['refresh_token']
    
    print(get_current_playing_track(ACCESS_TOKEN))

    token_refresh_thread = threading.Thread(target=refresh_Access_Token, daemon=True)
    token_refresh_thread.start()
    # ===============================================================================

    driver = Passenger(VETOS_PER_PASSENGER)
    passenger1 = Passenger(VETOS_PER_PASSENGER)
    passenger2 = Passenger(VETOS_PER_PASSENGER)
    passenger3 = Passenger(VETOS_PER_PASSENGER)

    # =================== GPIO ACTION ===============================================
    # Set up GPIO mode
    GPIO.setmode(GPIO.BCM)

    # Define the button pins
    BUTTONS = {
        1: {"pin": 17, "passenger": driver},
        2: {"pin": 18, "passenger": driver},
        3: {"pin": 22, "passenger": passenger1},
        4: {"pin": 20, "passenger": passenger1},
        5: {"pin": 21, "passenger": passenger2},
    }

    # Set up the GPIO pins for input
    for button, data in BUTTONS.items():
        GPIO.setup(data["pin"], GPIO.IN)

    try:
        while True:
            for button, data in BUTTONS.items():
                time.sleep(0.05)  # Add a small delay
                if GPIO.input(data["pin"]) < GPIO.HIGH:
                    if button % 2 == 0:
                        data["passenger"].skip()
                    else:
                        data["passenger"].veto()

    except KeyboardInterrupt:
        pass

    finally:
        GPIO.cleanup()  # Clean up the GPIO pins
    # ===============================================================================

def main():
    while True:
        # Present the menu options to the user
        print(Fore.MAGENTA + "\n========================")
        print(Fore.MAGENTA + " 1) Get Authorization Code")
        print(Fore.MAGENTA + " 2) Start Service")
        print(Fore.MAGENTA + " 3) Help")
        print(Fore.MAGENTA + " 4) Quit")
        print(Fore.MAGENTA + "========================\n")
        
        choice = input("Enter Choice: ")
        choice = choice.strip()

        if (choice == "1"):
            print(Fore.WHITE + "\nPlease visit the following URL and login to receive the authorization code:")
            print(Fore.WHITE + construct_Login_Url())
        elif (choice == "2"):
            start()
        elif (choice == "3"):
            print(Fore.WHITE + print_Help())
        elif (choice == "4"):
            print(Fore.YELLOW + "Exiting...")
            print(Fore.WHITE + "")
            exit()
        else:
            print(Fore.RED + "Invalid Option. Please Try Again.")


if __name__ == '__main__':
    main()