import os
import re
import time
import pandas as pd
import requests
from dotenv import load_dotenv
from termcolor import colored

# --- CONFIGURATION ---
# Loads the TMDB_API_KEY from the .env file in your project folder.
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"

# The folder where your final Markdown files will be saved.
MOVIES_DIR = "movies"

# IMPORTANT: Set this to the exact name of your Excel file.
# The file must be in the same directory as this script.
EXCEL_FILE_PATH = "film.xlsx"


def get_movie_credits(movie_id):
    """Fetches the director and top 5 actors for a given movie ID from TMDB."""
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
    """Creates a formatted Markdown file for a movie with YAML front matter."""
    # Generate a filesystem-safe version of the movie title for the filename.
    safe_title = "".join(c for c in details['title'] if c.isalnum() or c in (' ', '-')).rstrip()
    year = details.get('release_date', '0000')[:4]
    filename = f"{safe_title.replace(' ', '-')}-{year}.md"
    filepath = os.path.join(MOVIES_DIR, filename)

    if os.path.exists(filepath):
        print(colored(f"  -> File '{filename}' already exists. Skipping.", "yellow"))
        return

    # Define the structure of the YAML front matter.
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
    # Combine YAML and Markdown body into the final file content.
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


def main():
    """Main function to run the migration from the Excel file."""
    if not os.path.exists(EXCEL_FILE_PATH):
        print(colored(f"Error: Excel file not found at '{EXCEL_FILE_PATH}'.", "red"))
        return
        
    if not os.path.exists(MOVIES_DIR):
        os.makedirs(MOVIES_DIR)

    print(colored(f"--- Starting Migration from {EXCEL_FILE_PATH} ---", "magenta"))
    
    # Read the specified Excel file into a pandas DataFrame.
    df = pd.read_excel(EXCEL_FILE_PATH)
    
    # A helpful debug line to show the user what columns pandas has identified.
    print(colored(f"Found columns: {df.columns.tolist()}", "blue"))

    # Iterate over each row in the Excel sheet.
    for index, row in df.iterrows():
        # Access data by column POSITION (e.g., iloc[1] is the 2nd column).
        # This is more robust than using names, which can have typos.
        # Your Excel file should have: Title in Column B, Status in Column C.
        try:
            name_str = str(row.iloc[1]).strip()
            status_raw = row.iloc[2]
        except IndexError:
            print(colored(f"  -> Row {index + 1} is missing columns. Skipping.", "yellow"))
            continue

        print(colored(f"\nProcessing row {index + 1}: {name_str}", "cyan"))

        # Use regex to parse the year from the title string (e.g., "Parasite (2019)").
        match = re.search(r'\((\d{4})\)$', name_str)
        if match:
            year = match.group(1)
            title = name_str[:match.start()].strip()
        else:
            title = name_str
            year = None
            
        # Skip rows that are empty or couldn't be parsed.
        if not title or title.lower() == 'nan':
            print(colored("  -> No title found. Skipping row.", "yellow"))
            continue
            
        # Determine the movie's status. Defaults to 'to-watch' if not specified.
        status = 'watched' if pd.notna(status_raw) and str(status_raw).strip() == 'watched' else 'to-watch'

        # Search the TMDB API and create the corresponding markdown file.
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
            
            # Assume the first search result is the correct one for automation.
            movie_id = results[0]['id']
            print(f"  -> Found TMDB match: {results[0]['title']} ({results[0].get('release_date', 'N/A')[:4]})")
            
            details_response = requests.get(f"{TMDB_API_URL}/movie/{movie_id}", params={"api_key": TMDB_API_KEY})
            full_details = details_response.json()
            director, actors = get_movie_credits(movie_id)

            create_markdown_file(full_details, director, actors, status)
            
            # A short delay to be respectful of the TMDB API rate limits.
            time.sleep(0.25) 

        except Exception as e:
            print(colored(f"  -> An error occurred while processing '{title}': {e}", "red"))

    print(colored("\n--- Migration Complete ---", "magenta"))


# Standard entry point to run the script.
if __name__ == "__main__":
    main()