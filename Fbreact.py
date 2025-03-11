import os
import re
import requests
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore

# Initialize Colorama for colored output
init(autoreset=True)

# Machine Liker URLs
BASE_URL = "https://machineliker.net"
LOGIN_URL = f"{BASE_URL}/login"
REACTION_URL = f"{BASE_URL}/auto-reactions"

# Headers for HTTP requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-A037F) AppleWebKit/537.36"
}

class MachineLikerBot:
    def __init__(self):
        self.sessions = []
        self.post_url = ""
        self.reactions = []
        self.cookies = {}

    def login(self, fb_cookie, retry_attempts=3):
        """Log in to Machine Liker using Facebook session cookies with retries."""
        for attempt in range(1, retry_attempts + 1):
            try:
                session = requests.Session()
                response = session.get(LOGIN_URL, headers=HEADERS, cookies={"cookie": fb_cookie}, timeout=10)

                if "success" in response.text:
                    user_id = re.search(r'"id":"(\d+)"', response.text).group(1)
                    print(Fore.GREEN + f"[LOGIN SUCCESS] Logged in as User ID: {user_id}")
                    self.sessions.append(session)
                    return session
                elif "Invalid session" in response.text or response.status_code == 403:
                    print(Fore.RED + f"[LOGIN FAILED] Cookie expired or invalid. Removing from list.")
                    return None
                else:
                    print(Fore.YELLOW + f"[WARNING] Unexpected response on login attempt {attempt}. Retrying...")
                    sleep(3)
            except requests.RequestException as e:
                print(Fore.RED + f"[ERROR] Network issue on login attempt {attempt}: {e}")
                sleep(5)

        print(Fore.RED + "[ERROR] Login failed after multiple attempts. Skipping this account.")
        return None

    def get_cookies(self):
        """Prompt user to enter Facebook session cookies."""
        while True:
            try:
                num_cookies = int(input("How many Facebook cookies do you want to enter? (1-5): "))
                if 1 <= num_cookies <= 5:
                    break
                else:
                    print(Fore.RED + "Please enter a number between 1 and 5.")
            except ValueError:
                print(Fore.RED + "Invalid input. Please enter a number.")

        for i in range(num_cookies):
            fb_cookie = input(f"Enter cookie for Account {i + 1}: ").strip()
            if fb_cookie:
                self.cookies[f"cookie_{i + 1}"] = fb_cookie

    def select_reactions(self):
        """Allow the user to choose reactions to send."""
        reaction_map = {
            "1": "like", "2": "love", "3": "care", "4": "haha",
            "5": "wow", "6": "sad", "7": "angry"
        }

        print(Fore.YELLOW + "Select reactions (e.g., 123 for like, love, and care):")
        print(Fore.CYAN + "1: Like | 2: Love | 3: Care | 4: Haha | 5: Wow | 6: Sad | 7: Angry")
        
        while True:
            choices = input("Enter numbers: ")
            if all(c in reaction_map for c in choices):
                self.reactions = [reaction_map[c] for c in choices]
                break
            else:
                print(Fore.RED + "Invalid choice. Please enter valid numbers.")

    def boost_reactions(self, session, retry_attempts=3):
        """Send reaction boost request to Machine Liker with retries."""
        for attempt in range(1, retry_attempts + 1):
            try:
                get_token_page = session.get(REACTION_URL, timeout=10).text
                token_match = re.search(r'name="_token" value="(.*?)"', get_token_page)

                if not token_match:
                    print(Fore.RED + f"[ERROR] Could not retrieve CSRF token on attempt {attempt}. Retrying...")
                    sleep(3)
                    continue

                token = token_match.group(1)
                data = {
                    "url": self.post_url,
                    "limit": "50",
                    "reactions[]": self.reactions,
                    "_token": token
                }
                response = session.post(REACTION_URL, data=data, timeout=10).text

                if "Order Submitted" in response:
                    print(Fore.GREEN + "[SUCCESS] Reactions sent successfully!")
                    return
                elif "Cooldown" in response:
                    cooldown_time = int(re.search(r"please try again after (\d+) minutes", response).group(1)) * 60
                    print(Fore.YELLOW + f"[COOLDOWN] Waiting {cooldown_time} seconds...")
                    self.countdown(cooldown_time)
                    return
                else:
                    print(Fore.RED + f"[ERROR] Unexpected response on attempt {attempt}. Retrying...")
                    sleep(5)
            except requests.RequestException as e:
                print(Fore.RED + f"[ERROR] Network issue on attempt {attempt}: {e}")
                sleep(5)

        print(Fore.RED + "[ERROR] Failed to submit reactions after multiple attempts.")

    def countdown(self, seconds):
        """Display a countdown timer with an animation."""
        while seconds > 0:
            print(f"\r{Fore.YELLOW}[Cooldown] {seconds} seconds remaining...", end="")
            sleep(1)
            seconds -= 1
        print()

    def main(self):
        """Main execution function."""
        os.system("cls" if os.name == "nt" else "clear")

        # Get cookies and login
        self.get_cookies()
        with ThreadPoolExecutor(max_workers=5) as executor:
            for fb_cookie in self.cookies.values():
                session = executor.submit(self.login, fb_cookie).result()
                if session:
                    self.sessions.append(session)

        # Stop script if no valid sessions remain
        if not self.sessions:
            print(Fore.RED + "[ERROR] No valid sessions remaining. Exiting...")
            return

        # Get post URL and reaction type
        self.post_url = input(Fore.CYAN + "[INPUT] Enter the Facebook post URL to boost reactions: ")
        self.select_reactions()

        # Start boosting reactions
        while True:
            if not self.sessions:
                print(Fore.RED + "[ERROR] No valid sessions remaining. Exiting...")
                break

            for session in self.sessions:
                self.boost_reactions(session)

            self.countdown(1200)  # 20 minutes cooldown

if __name__ == "__main__":
    MachineLikerBot().main()
