import os

from garmin_ticket_login import migrate_pirate_token_to_garth


def migrate_token():
    pirate_path = os.path.expanduser("~/.local/share/pirate-garmin/native-oauth2.json")
    if not os.path.exists(pirate_path):
        print("Could not find pirate-garmin token file.")
        return
    migrate_pirate_token_to_garth(pirate_path)


if __name__ == "__main__":
    migrate_token()
