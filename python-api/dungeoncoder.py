import requests
import json
import os

def send_request(url: str, 
                 method: str = 'GET',
                 data: dict = None,
                 headers: dict = None, 
                 timeout = 1):
    try:
        if method == 'GET':
            response = requests.get(url, json=data, headers=headers, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        else:
            print(f"Error: Method {method} not implemented!")
            return None
        
        response.raise_for_status()
        return response

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} for URL: {url}")
    except requests.ConnectionError as conn_err:
        print(f"Connection error occurred. Did you start the Dungeon Coder Plugin?")
    except requests.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}. Server took too long to respond.")
    except requests.RequestException as req_err:
        print(f"An unexpected request error occurred: {req_err}")
    except requests.JSONDecodeError:
        print(f"Failed to decode JSON response from {url}. Response was:\n{response.text[:100]}...")
    except Exception as err:
        print(f"An unknown error occurred: {err}")
    return None 

def parse_api_response(response: requests.Response) -> bool:
    """
    Parses a successful HTTP response, checks for an API 'success' flag, 
    and raises a meaningful exception on failure.
    """
    if not response:
        return False
    
    if not response.content:
        return False

    try:
        data = response.json()
    except requests.JSONDecodeError:
        raise RuntimeError(f"Failed to decode JSON. Response: {response.text[:50]}...")

    if "status" in data and "result" in data:
        if data["status"] == "success":
            return data["result"]
        else:
            error_msg = data.get("message", "API response payload indicated failure.")
            raise RuntimeError(f"API operation failed: {error_msg}")
    
    return False

class Hero:
    """
    A class to control the hero's actions and get its state.
    """
    def __init__(self, base_url):
        self.BASE_URL = base_url       
   
    def configure(self, name: str, typeNumber: int):
        URL = f"{self.BASE_URL}/hero/configure"
        response = send_request(URL, 'POST', data={"name":name, "typeNumber": typeNumber})
        return parse_api_response(response)

    def move(self):
        """Sends a command to move the hero forward."""
        URL = f"{self.BASE_URL}/hero/move"
        response = send_request(URL, 'POST')
        return parse_api_response(response)

    def turn_left(self):
        """Sends a command to turn the hero to the left."""
        URL = f"{self.BASE_URL}/hero/turn_left"
        response = send_request(URL, 'POST')
        return parse_api_response(response)

    def interact(self):
        """Sends a command for the hero to interact with an object."""
        URL = f"{self.BASE_URL}/hero/interact"
        response = send_request(URL, 'POST')
        return parse_api_response(response)

    def is_collision_in_front(self):
        """Checks if there is a collision in front of the hero."""
        URL = f"{self.BASE_URL}/hero/is_collision_in_front"
        response = send_request(URL, 'GET')
        return parse_api_response(response)
    
    def is_switch_in_front(self):
        """Checks if there is a switch in front of the hero."""
        URL = f"{self.BASE_URL}/hero/is_switch_in_front"
        response = send_request(URL, 'GET')
        return parse_api_response(response)
    
    def is_facing_north(self):
        """Checks if the hero is facing north."""
        URL = f"{self.BASE_URL}/hero/is_facing_north"
        response = send_request(URL, 'GET')
        return parse_api_response(response)

    def is_torch_in_front(self):
        """Checks if there is a switch in front of the hero."""
        URL = f"{self.BASE_URL}/hero/is_torch_in_front"
        response = send_request(URL, 'GET')
        return parse_api_response(response)
    
    def is_at_goal(self):
        """Checks if the hero is at the goal."""
        URL = f"{self.BASE_URL}/hero/is_at_goal"
        response = send_request(URL, 'GET')
        return parse_api_response(response)

class Game:
    """
    A class to interact with the hero game API.
    
    Attributes:
        hero: An instance of Hero, which handles hero-related commands.
        level: An instance of Level, which handles level-related commands.
    """
    
    BASE_URL = "http://localhost:3000"

    def __init__(self, level_file):
        self.__level = self.Level(self.BASE_URL)
        try:
            self.__level.load(level_file)
        except:
            print(f"Error: Level {level_file} could not be loaded. Please make sure the file exists and is valid.")

        self.__hero = Hero(self.BASE_URL)

    def get_hero(self):
        return self.__hero

    class Level:
        """
        A class to manage game levels.
        """
        def __init__(self, base_url):
            self.BASE_URL = base_url

        def load(self, filename):
            """
            Loads a level from a JSON file.
            
            Args:
                filename (str): The path to the JSON file containing the level data.
            """
            if not os.path.exists(filename):
                return {"status": "error", "message": f"File not found: {filename}"}
            
            with open(filename, 'r') as f:
                level_data = json.load(f)
            headers = {"Content-Type": "application/json"}
            URL = f"{self.BASE_URL}/level/load"

            response = send_request(URL, 'POST', level_data, headers)
            return parse_api_response(response)

        def reset(self):
            """Resets the current level."""
            URL = f"{self.BASE_URL}/level/reset"
            response = send_request(URL, 'POST')
            return parse_api_response(response)
