import os
import requests
import pandas as pd
from dotenv import load_dotenv
from termcolor import colored
import time
import re

# --- CONFIGURATION ---
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"
MOVIES_DIR = "movies"
# --- FIX #1: Use the correct Excel file name ---
EXCEL_FILE_PATH = "film.xlsx"

# --- HELPER FUNCTIONS (No changes here) ---

def get_movie_credits(movie_id):
    """Efficiently fetches both the director and top actors."""
    try:
        response = requests.get(f"{TMDB_API_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits")
        response.raise_for_status()
        data = response.json()
        director = "Unknown"
        for member in data.get('credits', {}).get('crew', []):
            if member.get('job') == 'Director':
                director = member.get('name')
                break
        actors = [actor['name'] for actor in data.get('credits', {}).get('cast', [])[:5]]
        return director, actors
    except requests.exceptions.RequestException:
        return "Unknown", []

def create_markdown_file(details, director, actors, status):
    """Creates a markdown file from the migrated data."""
    safe_title = "".join(c for c in details['title'] if c.isalnum() or c in (' ', '-')).rstrip()
    year = details.get('release_date', '0000')[:4]
    filename = f"{safe_title.replace(' ', '-')}-{year}.md"
    filepath = os.path.join(MOVIES_DIR, filename)

    if os.path.exists(filepath):
        print(colored(f"  -> File '{filename}' already exists. Skipping.", "yellow"))
        return

    yaml_content = f"""
title: "{details['title']}"
year: {year}
director: "{director}"
runtime: {details.get('runtime', 0)}
genres:
  - {"\n  - ".join([genre['name'] for genre in details.get('genres', [])])}
rating: 0.0
status: "{status}"
date_watched:
actors:
  - {"\n  - ".join(actors)}
countries:
  - {"\n  - ".join([country['name'] for country in details.get('production_countries', [])])}
original_language: "{details.get('original_language', 'N/A').upper()}"
spoken_languages:
  - {"\n  - ".join([lang['english_name'] for lang in details.get('spoken_languages', [])])}
release_date: "{details.get('release_date', 'N/A')}"
poster_path: "https://image.tmdb.org/t/p/w500{details.get('poster_path', '')}"
"""
    content = f"""---{yaml_content.strip()}
---
## Synopsis
{details.get('overview', 'No synopsis available.')}
## My Notes
(Your thoughts go here)
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(colored(f"  -> Successfully created file: {filename}", "green"))

# --- MAIN MIGRATION LOGIC ---

def main():
    if not os.path.exists(EXCEL_FILE_PATH):
        print(colored(f"Error: Excel file not found at '{EXCEL_FILE_PATH}'. Make sure it's in the same folder.", "red"))
        return
        
    if not os.path.exists(MOVIES_DIR):
        os.makedirs(MOVIES_DIR)

    print(colored(f"--- Starting Migration from {EXCEL_FILE_PATH} ---", "magenta"))
    
    # Read the Excel file, assuming the first row is the header
    df = pd.read_excel(EXCEL_FILE_PATH)
    
    # --- FIX #2: Access columns by POSITION to avoid name errors ---
    # Print the column headers that pandas found, for debugging.
    print(colored(f"Found columns: {df.columns.tolist()}", "blue"))

    for index, row in df.iterrows():
        # Use .iloc[1] to get data from the SECOND column (Movie Title)
        # Use .iloc[2] to get data from the THIRD column (Status)
        try:
            name_str = str(row.iloc[1]).strip()
            status_raw = row.iloc[2]
        except IndexError:
            print(colored(f"  -> Could not read columns for row {index + 1}. Skipping.", "yellow"))
            continue

        print(colored(f"\nProcessing row {index + 1}: {name_str}", "cyan"))

        match = re.search(r'\((\d{4})\)$', name_str)
        if match:
            year = match.group(1)
            title = name_str[:match.start()].strip()
        else:
            title = name_str
            year = None
            
        if not title or title.lower() == 'nan':
            print(colored("  -> No title found. Skipping row.", "yellow"))
            continue
            
        status = 'watched' if pd.notna(status_raw) and str(status_raw).strip() == 'watched' else 'to-watch'

        try:
            search_params = {"api_key": TMDB_API_KEY, "query": title}
            if year:
                search_params['year'] = year

            search_response = requests.get(f"{TMDB_API_URL}/search/movie", params=search_params)
            search_response.raise_for_status()
            results = search_response.json().get('results', [])

            if not results:
                print(colored(f"  -> No API results found for '{title} ({year})'. Skipping.", "red"))
                continue
            
            movie_id = results[0]['id']
            print(f"  -> Found TMDB match: {results[0]['title']} ({results[0].get('release_date', 'N/A')[:4]})")
            
            details_response = requests.get(f"{TMDB_API_URL}/movie/{movie_id}", params={"api_key": TMDB_API_KEY})
            full_details = details_response.json()
            director, actors = get_movie_credits(movie_id)

            create_markdown_file(full_details, director, actors, status)
            
            time.sleep(0.25) 

        except Exception as e:
            print(colored(f"  -> An error occurred for '{title}': {e}", "red"))

    print(colored("\n--- Migration Complete ---", "magenta"))

if __name__ == "__main__":
    main()