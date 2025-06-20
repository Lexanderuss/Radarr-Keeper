# radarr-tool/app/radarr_client.py
# FINALE VERSION, BASIEREND AUF IHREM FUNKTIONIERENDEN CODE

import requests

class RadarrClient:
    def __init__(self, url, api_key):
        if not url or not api_key:
            raise ValueError("Radarr URL and API Key must be provided.")
        self.base_url = f"{url.rstrip('/')}/api/v3"
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'X-Api-Key': api_key, "Content-Type": "application/json"})

    def get_movies(self):
        try:
            response = self.session.get(f"{self.base_url}/movie", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException: return None

    def delete_movie(self, movie_id, delete_files=True, add_import_exclusion=False):
        params = {'deleteFiles': str(delete_files).lower(), 'addImportExclusion': str(add_import_exclusion).lower()}
        try:
            response = self.session.delete(f"{self.base_url}/movie/{movie_id}?{'&'.join([f'{k}={v}' for k, v in params.items()])}", timeout=15)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException: return False

    def get_exclusions(self):
        try:
            # Der Endpunkt zum Abrufen heißt ebenfalls /exclusions
            response = self.session.get(f"{self.base_url}/exclusions", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException: return None

    def add_exclusion(self, tmdb_id, title, year):
        """
        Implementiert exakt Ihre funktionierende Logik.
        """
        if not year or year < 1900:
            return False, "Kein gültiges Jahr übergeben"

        url = f"{self.base_url}/exclusions"
        payload = {
            "tmdbId": tmdb_id,
            "movieTitle": title,
            "movieYear": year
        }
        try:
            response = self.session.post(url, json=payload, timeout=15)
            # Erfolgreich erstellt
            if response.status_code == 201:
                return True, "Created"
            # Bereits vorhanden (Konflikt) - wir werten das auch als "Erfolg"
            elif response.status_code == 409:
                return True, "Conflict - Already Exists"
            # Alle anderen Fehler
            else:
                return False, f"HTTP {response.status_code} - {response.text}"
        except requests.exceptions.RequestException as e:
            return False, str(e)

    def remove_exclusion(self, exclusion_id):
        try:
            # Der Endpunkt für das Löschen heißt /exclusions/ID
            response = self.session.delete(f"{self.base_url}/exclusions/{exclusion_id}", timeout=15)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException: return False