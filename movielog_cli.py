import os
import re
import math
import time
import yaml
import requests
from collections import Counter
from datetime import date
from dotenv import load_dotenv
from termcolor import colored

# ==============================================================================
# --- CONFIGURATION & SETUP ---
# ==============================================================================

# Load environment variables (specifically TMDB_API_KEY) from the .env file.
load_dotenv()

# --- Global Constants ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOVIES_DIR = os.path.join(SCRIPT_DIR, "movies")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"
ACTOR_COUNT = 5  # Number of actors to list in the movie files.

# ==============================================================================
# --- CORE HELPER FUNCTIONS ---
# ==============================================================================

def clear_screen():
    """Clears the terminal screen for a cleaner UI."""
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_yaml_front_matter(content, filename):
    """Extracts and parses the YAML front matter from a Markdown file's content."""
    match = re.search(r'---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            print(colored(f"[Warning] YAML Error in {filename}: {e}", "yellow"))
            return None
    return None

def load_movie_data():
    """Reads all .md files in the MOVIES_DIR, parses their YAML, and returns a list."""
    all_movies = []
    print("Loading all movie data from disk...")
    if not os.path.exists(MOVIES_DIR):
        print(colored(f"Movies directory not found at '{MOVIES_DIR}'.", "red"))
        time.sleep(2)
        return []

    files_to_process = [f for f in os.listdir(MOVIES_DIR) if f.endswith(".md")]
    for filename in files_to_process:
        filepath = os.path.join(MOVIES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = parse_yaml_front_matter(f.read(), filename)
            if data:
                # Add the file's path to the data for easy access later (e.g., viewing details).
                data['filepath'] = filepath
                all_movies.append(data)

    print(colored(f"Successfully loaded and parsed {len(all_movies)} movie files.", "green"))
    # A brief pause to allow the user to read the confirmation message.
    time.sleep(1.5)
    return all_movies

# ==============================================================================
# --- FEATURE 1: LOG A NEW MOVIE ---
# ==============================================================================

def run_movie_logger():
    """Guides the user through searching for and logging a new movie."""
    clear_screen()
    print(colored("--- ✍️ Log a New Movie ---", "magenta", attrs=["bold"]))

    if not TMDB_API_KEY:
        print(colored("Error: TMDB_API_KEY not found in .env file.", "red"))
        return

    search_query = input(colored("Enter movie title: ", "cyan"))

    try:
        # Step 1: Search TMDB for the movie.
        res = requests.get(f"{TMDB_API_URL}/search/movie", params={"api_key": TMDB_API_KEY, "query": search_query})
        res.raise_for_status()
        results = res.json().get('results', [])
        if not results:
            print(colored("No movies found.", "red"))
            return

        # Step 2: Display results and get user's choice.
        for i, m in enumerate(results[:10]):
            print(f"  {colored(f'{i+1}:', 'yellow')} {m['title']} ({m.get('release_date', 'N/A')[:4]})")
        choice = int(input(colored("\nEnter number: ", "cyan"))) - 1
        selected = results[choice]

        # Step 3: Get user input for status, rating, and personal notes.
        status = 'watched' if input(colored("Status (w/watched or tw/to-watch): ", "cyan")).lower() in ['w', 'watched'] else 'to-watch'
        rating = float(input(colored("Rating (1-10): ", "cyan"))) if status == 'watched' else 0.0
        notes = ""
        if input(colored("Add notes? (y/n): ", "cyan")).lower() in ['y', 'yes']:
            print(colored("Enter notes. Press Enter on an empty line to finish.", "yellow"))
            notes = "\n".join(iter(input, ""))

        # Step 4: Fetch full movie details, including credits.
        details_res = requests.get(f"{TMDB_API_URL}/movie/{selected['id']}", params={"api_key": TMDB_API_KEY, "append_to_response": "credits"})
        details = details_res.json()
        director = next((m['name'] for m in details.get('credits', {}).get('crew', []) if m.get('job') == 'Director'), "Unknown")
        actors = [a['name'] for a in details.get('credits', {}).get('cast', [])[:ACTOR_COUNT]]

        # Step 5: Construct the file path and content.
        safe_title = "".join(c for c in details.get('title', '') if c.isalnum() or c in (' ', '-')).rstrip()
        year = details.get('release_date', '0000')[:4]
        filename = f"{safe_title.replace(' ', '-')}-{year}.md"
        filepath = os.path.join(MOVIES_DIR, filename)

        if not os.path.exists(MOVIES_DIR): os.makedirs(MOVIES_DIR)
        if os.path.exists(filepath):
            print(colored(f"\nFile '{filename}' already exists.", "yellow"))
            return

        yaml_content = f"""
title: "{details.get('title', 'N/A').replace('"', "'")}"
year: {int(year) if year.isdigit() else 'null'}
director: "{director.replace('"', "'")}"
runtime: {details.get('runtime', 0)}
genres:
  - {"\n  - ".join([g.get('name', '') for g in details.get('genres', [])])}
rating: {rating}
status: "{status}"
date_watched: {date.today().isoformat() if status == "watched" else ''}
actors:
  - {"\n  - ".join(actors)}
countries:
  - {"\n  - ".join([c.get('name', '') for c in details.get('production_countries', [])])}
original_language: "{details.get('original_language', 'N/A').upper()}"
release_date: "{details.get('release_date', '')}"
poster_path: "https://image.tmdb.org/t/p/w500{details.get('poster_path', '')}"
"""
        content = f"---\n{yaml_content.strip()}\n---\n\n## Synopsis\n\n{details.get('overview', '')}\n\n## My Notes\n\n{notes if notes else '(Your thoughts go here)'}"

        # Step 6: Write the new movie file to disk.
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(colored(f"\nSuccessfully created file: {filename}", "green"))

    except Exception as e:
        print(colored(f"An error occurred: {e}", "red"))

    input(colored("\nPress Enter to return...", "cyan"))

# ==============================================================================
# --- UI FEATURE MODULES (Browse, Stats, Search) ---
# ==============================================================================

def display_paginated_list(title, data_list, is_movie_list=False):
    """Generic function to display a paginated list in the terminal."""
    if not data_list:
        clear_screen()
        print(colored(f"No data available for '{title}'", "yellow"))
        input("\nPress Enter...")
        return

    page, page_size = 0, 15
    total_pages = math.ceil(len(data_list) / page_size)

    while True:
        clear_screen()
        print(colored(f"--- 📜 {title} ---", "magenta", attrs=["bold"]))
        print(colored(f"Page {page + 1} of {total_pages}\n", "yellow"))

        # Display the items for the current page.
        start_index = page * page_size
        end_index = start_index + page_size
        current_page_items = data_list[start_index:end_index]

        for i, item in enumerate(current_page_items, start=start_index):
            if is_movie_list:
                print(f"  {i+1:>3}. {item.get('title', 'N/A')} ({item.get('year', 'N/A')})")
            else: # Assumes item is a tuple (e.g., from Counter)
                display_item, count = item
                print(f"  {i+1:>3}. {str(display_item or 'N/A'):<30} ({count})")

        # Navigation controls.
        nav_prompt = "[n]ext, [p]rev, [q]uit"
        if is_movie_list:
            nav_prompt += ", or # to view details"
        print("\n" + colored(nav_prompt, "cyan"))
        choice = input("Navigation: ").lower()

        if choice == 'n' and page < total_pages - 1:
            page += 1
        elif choice == 'p' and page > 0:
            page -= 1
        elif choice == 'q':
            break
        elif is_movie_list:
            # Handle drill-down to view a movie's full file content.
            try:
                choice_num = int(choice)
                if start_index < choice_num <= end_index:
                    selected_movie = data_list[choice_num - 1]
                    clear_screen()
                    print(colored(f"--- Details for: {selected_movie.get('title')} ---", "magenta"))
                    with open(selected_movie['filepath'], 'r', encoding='utf-8') as f:
                        print(f.read())
                    input(colored("\nPress Enter to return to the list...", "cyan"))
            except (ValueError, IndexError):
                pass

def run_browse_list(movies):
    """Filters and displays the 'to-watch' list."""
    to_watch_list = sorted([m for m in movies if m.get("status") == "to-watch"], key=lambda x: x.get('year') or 9999)
    display_paginated_list("Browse Your 'To-Watch' List", to_watch_list, is_movie_list=True)

def run_stats_viewer(movies):
    """Calculates and displays a dashboard of statistics for watched movies."""
    watched = [m for m in movies if m.get('status') == 'watched']
    if not watched:
        input(colored("No 'watched' movies found to generate stats. Press Enter.", "red"))
        return

    # Pre-calculate all statistics for efficiency.
    stats = {
        "total_watched": len(watched),
        "total_hours": sum(m.get('runtime', 0) for m in watched if m.get('runtime')) / 60,
        "avg_rating": sum(m.get('rating', 0) for m in watched if m.get('rating')) / len([m for m in watched if m.get('rating')]) if any(m.get('rating') for m in watched) else 0,
        "top_directors": Counter(m['director'] for m in watched if m.get('director')).most_common(),
        "top_genres": Counter(g for m in watched if m.get('genres') for g in m['genres']).most_common(),
        "by_decade": Counter(math.floor(int(m['year']) / 10) * 10 for m in watched if m.get('year') and isinstance(m.get('year'), int)).most_common(),
        "rating_distribution": Counter(round(m['rating']) for m in watched if m.get('rating')).most_common()
    }
    sorted_decades = sorted(stats['by_decade'], key=lambda x: x[0], reverse=True)

    # Main stats dashboard loop.
    while True:
        clear_screen()
        print(colored("--- 🍿 Your Movie Stats Dashboard 🍿 ---", "magenta", attrs=["bold"]))
        print("\n" + colored("📊 At a Glance", "cyan"))
        print(f"  - Movies Watched: {colored(stats['total_watched'], 'green')}")
        print(f"  - Total Watch Time: {colored(f'{stats['total_hours']:.1f} hours', 'green')}")
        print(f"  - Average Rating: {colored(f'{stats['avg_rating']:.2f} / 10', 'green')}")

        print("\n" + colored("⭐ Rating Distribution", "cyan"))
        max_rating_count = max(c for r, c in stats['rating_distribution']) if stats['rating_distribution'] else 0
        for rating, count in sorted(stats['rating_distribution']):
            bar = "█" * int((count / max_rating_count) * 25) if max_rating_count > 0 else ""
            print(f"  {str(rating):>2}/10 | {bar} ({count})")

        print("\n" + colored("--- 🔎 Dig Deeper ---", "magenta"))
        print("  1. Top Genres")
        print("  2. Top Directors")
        print("  3. Movies by Decade")
        print(colored("  b. Back to Main Menu", "red"))
        choice = input(colored("\nSelect an option: ", "cyan")).lower()
        
        if choice == '1': display_paginated_list("Top Genres", stats['top_genres'])
        elif choice == '2': display_paginated_list("Top Directors", stats['top_directors'])
        elif choice == '3': display_paginated_list("Movies by Decade", sorted_decades)
        elif choice == 'b': break

def run_search_menu(all_movies):
    """Provides a menu for searching the local movie collection by various fields."""
    while True:
        clear_screen()
        print(colored("======= 🔎 MOVIE SEARCH =======", "green", attrs=["bold"]))
        print("Choose a method to search your collection.\n")
        print("  1. Search by Title")
        print("  2. Search by Director")
        print("  3. Search by Actor")
        print("  4. Universal Keyword Search")
        print(colored("  b. Back to Main Menu", "red"))
        choice = input(colored("\nSelect a search method: ", "cyan")).lower()
        
        results = []
        query = ""

        if choice == '1':
            query = input("Enter title: ").lower()
            results = [m for m in all_movies if m.get('title') and query in m['title'].lower()]
        elif choice == '2':
            query = input("Enter director: ").lower()
            results = [m for m in all_movies if m.get('director') and query in m['director'].lower()]
        elif choice == '3':
            query = input("Enter actor: ").lower()
            results = [m for m in all_movies if any(a and query in a.lower() for a in m.get('actors', []))]
        elif choice == '4':
            query = input("Enter keyword: ").lower()
            results = [m for m in all_movies if any([
                m.get('title') and query in m.get('title', '').lower(),
                m.get('director') and query in m.get('director', '').lower(),
                any(g and query in g.lower() for g in m.get('genres', [])),
                any(a and query in a.lower() for a in m.get('actors', []))
            ])]
        elif choice == 'b':
            break

        if query:
            display_paginated_list(f"Search Results for '{query}'", results, is_movie_list=True)


# ==============================================================================
# --- MAIN APPLICATION LOOP ---
# ==============================================================================

def main_menu():
    """The main entry point and menu for the CLI application."""
    # Load all movie data once at the start for performance.
    all_movies = load_movie_data()
    
    while True:
        clear_screen()
        print(colored("======= MOVIELOG CLI =======", "green", attrs=["bold"]))
        print(f"Your personal movie logger. ({len(all_movies)} movies loaded)\n")
        print("  1. ✍️  Log a New Movie")
        print("  2. 📚  Browse 'To-Watch' List")
        print("  3. 📊  View Stats Dashboard")
        print("  4. 🔎  Search Your Collection")
        print(colored("  q. 👋  Quit", "red"))
        choice = input(colored("\nWhat would you like to do? ", "cyan")).lower()

        if choice == '1':
            run_movie_logger()
            # Reload data to reflect the newly added movie.
            all_movies = load_movie_data()
        elif choice == '2':
            run_browse_list(all_movies)
        elif choice == '3':
            run_stats_viewer(all_movies)
        elif choice == '4':
            run_search_menu(all_movies)
        elif choice == 'q':
            print(colored("Happy movie watching!", "green"))
            break

# Standard Python entry point.
if __name__ == "__main__":
    main_menu()