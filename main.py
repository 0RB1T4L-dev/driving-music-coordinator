import SECRETS
import requests
from colorama import Fore
import time
import threading
import keyboard

ACCESS_TOKEN = None
REFRESH_TOKEN = None

SKIP_COUNTER = 0
CURRENT_VETO_SONG_ID = 0

class Passenger:
    def __init__(self, veto_counter: int, gpio_pins: int [2]):
        self.veto_counter = veto_counter
        self.gpio_pins = gpio_pins
        self.last_song_skipped = "0"
    
    def skip(self):
        current_song_id = get_current_playing_track(ACCESS_TOKEN).item.id

        if current_song_id == CURRENT_VETO_SONG_ID:
            print("Song is protected by veto")
            return

        if current_song_id != self.last_song_skipped:
            self.last_song_skipped = current_song_id
            SKIP_COUNTER += 1

            if SKIP_COUNTER > 2:
                skip_track(ACCESS_TOKEN)
                SKIP_COUNTER = 0
    
    def veto(self):
        SKIP_COUNTER = 0
        CURRENT_VETO_SONG_ID = get_current_playing_track(ACCESS_TOKEN).item.id


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
        track_data = response.json()
        
        # Extract relevant details (track name, artist, album)
        if track_data:
            track_info = {
                "track_name": track_data["item"]["name"],
                "artist_name": ", ".join(artist["name"] for artist in track_data["item"]["artists"]),
                "album_name": track_data["item"]["album"]["name"],
                "is_playing": track_data["is_playing"]
            }
            return track_info
        else:
            return None
    
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
    while True:
        print(f"Refreshing Token with {REFRESH_TOKEN}")
        time.sleep(5)

def on_Key_Event(event):
    print(f"Key '{event.name}' pressed!")

def on_GPIO_Event():
    print("TODO")


def start():
    initial_access = get_Initial_Access_And_Refresh_Token()
    #initial_access = {'access_token': 'BQCcp89YsEAHxO9aFQg_bHEVuNb0hnAwP6PwvY7l2NhkelgKLEyIooBmEko_CfNXa0JtkoUZenj_m_yD1khiB6z3vs5yDRfA7r3NpvLcEENFs83rWUI7Jtd6XAkcKFnUMI2vpsNJdD3JzOMAlgRlPtvYbAdfCms4g_9LsopmNVWXTyvn51o4cLJe2kf0mj1uXP7WjCiQ37wNabpE71hp', 'token_type': 'Bearer', 'expires_in': 3600, 'refresh_token': 'AQDZX0b4QIoZBni3bvP4orUHN2gGb-qDZAF3zYX5iwJrhj8bJ5Rfcrrsat1OSH2QlOgKXKOykITSVTwNYBga3i8mK2uPdU3XDBlVLIjsCgu441zeahnqUQ_rZj9_nU5jNWQ', 'scope': 'user-modify-playback-state user-read-currently-playing'}

    ACCESS_TOKEN = initial_access['access_token']
    REFRESH_TOKEN = initial_access['refresh_token']
    
    #print(get_current_playing_track(ACCESS_TOKEN))
    #skip_track(ACCESS_TOKEN)

    token_refresh_thread = threading.Thread(target=refresh_Access_Token, args=("access1", "refresh1"), daemon=True)
    #token_refresh_thread.start()

    keyboard.on_press(on_Key_Event)
    keyboard.wait('q')



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