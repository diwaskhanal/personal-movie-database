import os
import yaml
import re
from collections import Counter
from termcolor import colored
import time
from datetime import date
import requests
from dotenv import load_dotenv
import math

# ==============================================================================
# --- CONFIGURATION & SETUP ---
# ==============================================================================
load_dotenv()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOVIES_DIR = os.path.join(SCRIPT_DIR, "movies")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URL = "https://api.themoviedb.org/3"
ACTOR_COUNT = 5

# --- HELPER: CLEAR SCREEN ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# --- DATA LOADING (STORES FILEPATH FOR DRILL-DOWN) ---
def parse_yaml_front_matter(content, filename):
    match = re.search(r'---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        try: return yaml.safe_load(match.group(1))
        except yaml.YAMLError as e: print(colored(f"[Warning] YAML Error in {filename}: {e}", "yellow")); return None
    return None

def load_movie_data():
    all_movies = []
    print("Loading all movie data from disk...")
    if not os.path.exists(MOVIES_DIR):
        print(colored(f"Movies directory not found at '{MOVIES_DIR}'.", "red")); time.sleep(2); return []
    files_to_process = [f for f in os.listdir(MOVIES_DIR) if f.endswith(".md")]
    for filename in files_to_process:
        filepath = os.path.join(MOVIES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = parse_yaml_front_matter(f.read(), filename)
            if data:
                data['filepath'] = filepath
                all_movies.append(data)
    print(colored(f"Successfully loaded and parsed {len(all_movies)} movie files.", "green"))
    time.sleep(1.5)
    return all_movies

# ==============================================================================
# --- FEATURE 1: LOG A NEW MOVIE ---
# ==============================================================================
def run_movie_logger():
    clear_screen(); print(colored("--- ✍️ Log a New Movie ---", "magenta", attrs=["bold"]))
    if not TMDB_API_KEY: print(colored("Error: TMDB_API_KEY not found.", "red")); return
    search_query = input(colored("Enter movie title: ", "cyan"))
    try:
        res = requests.get(f"{TMDB_API_URL}/search/movie", params={"api_key": TMDB_API_KEY, "query": search_query}); res.raise_for_status(); results = res.json().get('results', [])
        if not results: print(colored("No movies found.", "red")); return
        for i, m in enumerate(results[:10]): print(f"  {colored(f'{i+1}:', 'yellow')} {m['title']} ({m.get('release_date', 'N/A')[:4]})")
        choice = int(input(colored("\nEnter number: ", "cyan"))) -1; selected = results[choice]
        status = 'watched' if input(colored("Status (w/watched or tw/to-watch): ", "cyan")).lower() in ['w', 'watched'] else 'to-watch'
        rating = float(input(colored("Rating (1-10): ", "cyan"))) if status == 'watched' else 0.0
        notes = "\n".join(iter(input, "")) if input(colored("Add notes? (y/n): ", "cyan")).lower() in ['y', 'yes'] else ""
        details_res = requests.get(f"{TMDB_API_URL}/movie/{selected['id']}", params={"api_key": TMDB_API_KEY, "append_to_response":"credits"}); details = details_res.json()
        director = next((m['name'] for m in details.get('credits',{}).get('crew',[]) if m.get('job')=='Director'), "Unknown"); actors = [a['name'] for a in details.get('credits',{}).get('cast',[])[:ACTOR_COUNT]]
        safe_title = "".join(c for c in details.get('title', '') if c.isalnum() or c in (' ', '-')).rstrip(); year = details.get('release_date', '0000')[:4]; filename = f"{safe_title.replace(' ', '-')}-{year}.md"
        filepath = os.path.join(MOVIES_DIR, filename)
        if not os.path.exists(MOVIES_DIR): os.makedirs(MOVIES_DIR)
        if os.path.exists(filepath): print(colored(f"\nFile '{filename}' already exists.", "yellow")); return
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
        with open(filepath, 'w', encoding='utf-8') as f: f.write(content); print(colored(f"\nSuccessfully created file: {filename}", "green"))
    except Exception as e: print(colored(f"An error occurred: {e}", "red"))
    input(colored("\nPress Enter to return...", "cyan"))

# ==============================================================================
# --- FEATURE 2: BROWSE 'TO-WATCH' LIST ---
# ==============================================================================
def run_browse_list():
    movies = load_movie_data()
    to_watch_list = sorted([m for m in movies if m.get("status") == "to-watch"], key=lambda x: x.get('year') or 9999)
    if not to_watch_list:
        clear_screen(); print(colored("Your 'To-Watch' list is empty!", "green")); input("\nPress Enter..."); return
    page, page_size = 0, 15; total_pages = math.ceil(len(to_watch_list) / page_size)
    while True:
        clear_screen(); print(colored("--- 📚 Browse Your 'To-Watch' List ---", "magenta", attrs=["bold"])); print(colored(f"Page {page + 1} of {total_pages}\n", "yellow"))
        start_index = page * page_size; end_index = start_index + page_size
        current_page_movies = to_watch_list[start_index:end_index]
        for i, movie in enumerate(current_page_movies, start=start_index): print(f"  {i+1:>3}. {movie.get('title', 'N/A')} ({movie.get('year', 'N/A')})")
        print("\n" + colored("[n]ext, [p]rev, [q]uit, or # to view details", "cyan")); choice = input("Navigation: ").lower()
        if choice == 'n' and page < total_pages - 1: page += 1
        elif choice == 'p' and page > 0: page -= 1
        elif choice == 'q': break
        else:
            try:
                choice_num = int(choice)
                if start_index < choice_num <= end_index:
                    selected_movie = to_watch_list[choice_num - 1]
                    clear_screen(); print(colored(f"--- Details for: {selected_movie.get('title')} ---", "magenta"))
                    with open(selected_movie['filepath'], 'r', encoding='utf-8') as f: print(f.read())
                    input(colored("\nPress Enter to return to the list...", "cyan"))
            except (ValueError, IndexError): pass

# ==============================================================================
# --- FEATURE 3: VIEW STATS DASHBOARD ---
# ==============================================================================
def create_bar(value, max_value, length=20):
    if max_value == 0: return ""
    fill_len = int((value / max_value) * length); return "█" * fill_len + "░" * (length - fill_len)

def display_paginated_list(title, data_list):
    if not data_list:
        clear_screen(); print(colored(f"No data available for '{title}'", "yellow")); input("\nPress Enter..."); return
    page, page_size = 0, 15; total_pages = math.ceil(len(data_list) / page_size)
    while True:
        clear_screen(); print(colored(f"--- 📜 Full List: {title} ---", "magenta", attrs=["bold"])); print(colored(f"Page {page + 1} of {total_pages}\n", "yellow"))
        for i, (item, count) in enumerate(data_list[page*page_size : (page+1)*page_size], start=page*page_size):
            display_item = str(item or "N/A"); print(f"  {i+1:>3}. {display_item:<30} ({count})")
        print("\n" + colored("[n]ext, [p]rev, [q]uit", "cyan")); choice = input("Navigation: ").lower()
        if choice == 'n' and page < total_pages - 1: page += 1
        elif choice == 'p' and page > 0: page -= 1
        elif choice == 'q': break

def display_leaderboard(title, movies, field, sort_asc=False, limit=15):
    clear_screen(); print(colored(f"--- 🏆 Leaderboard: {title} ---", "magenta", attrs=["bold"]))
    filtered_movies = [m for m in movies if m.get(field) and m[field] > 0]
    sorted_movies = sorted(filtered_movies, key=lambda x: x.get(field, 0), reverse=not sort_asc)
    for movie in sorted_movies[:limit]:
        value = movie.get(field, 'N/A'); display_value = f"{value} min" if field == 'runtime' else value
        print(f"  - {movie.get('title', 'Unknown'):<35} ({display_value})")
    input(colored("\nPress Enter to return...", "cyan"))

def run_stats_viewer():
    movies = load_movie_data(); watched = [m for m in movies if m.get('status') == 'watched']
    if not watched: input(colored("No 'watched' movies for stats. Press Enter.", "red")); return
    stats = {
        "total_watched": len(watched),
        "total_hours": sum(m.get('runtime', 0) for m in watched if m.get('runtime')) / 60,
        "avg_rating": sum(m.get('rating', 0) for m in watched if m.get('rating')) / len([m for m in watched if m.get('rating')]) if any(m.get('rating') for m in watched) else 0,
        "top_directors": Counter(m['director'] for m in watched if m.get('director')).most_common(),
        "top_genres": Counter(g for m in watched if m.get('genres') for g in m['genres']).most_common(),
        "top_actors": Counter(a for m in watched if m.get('actors') for a in m['actors']).most_common(),
        "top_countries": Counter(c for m in watched if m.get('countries') for c in m['countries']).most_common(),
        "by_decade": Counter(math.floor(int(m['year']) / 10) * 10 for m in watched if m.get('year') and isinstance(m.get('year'), int)).most_common(),
        "rating_distribution": Counter(round(m['rating']) for m in watched if m.get('rating')).most_common()
    }
    sorted_decades = sorted(stats['by_decade'], key=lambda x: x[0], reverse=True)
    while True:
        clear_screen(); print(colored("--- 🍿 Your Movie Stats Dashboard 🍿 ---", "magenta", attrs=["bold"]))
        print("\n" + colored("📊 At a Glance", "cyan")); print(f"  - Movies Watched: {colored(stats['total_watched'], 'green')}")
        print(f"  - Total Watch Time: {colored(f'{stats['total_hours']:.1f} hours', 'green')}"); print(f"  - Average Rating: {colored(f'{stats['avg_rating']:.2f} / 10', 'green')}")
        print("\n" + colored("⭐ Rating Distribution", "cyan"))
        max_rating_count = max(c for r, c in stats['rating_distribution']) if stats['rating_distribution'] else 0
        for rating, count in sorted(stats['rating_distribution']): print(f"  {str(rating):>2}/10 | {create_bar(count, max_rating_count, 25)} ({count})")
        print("\n" + colored("--- 🔎 Dig Deeper ---", "magenta")); print("  1. Top Genres"); print("  2. Top Directors"); print("  3. Top Actors")
        print("  4. Top Countries"); print("  5. Movies by Decade"); print("\n  --- Leaderboards ---"); print("  6. Highest Rated Movies")
        print("  7. Lowest Rated Movies"); print("  8. Longest Movies"); print("  9. Shortest Movies"); print(colored("  b. Back to Main Menu", "red"))
        choice = input(colored("\nSelect an option: ", "cyan")).lower()
        menu = {'1': lambda: display_paginated_list("Top Genres", stats['top_genres']),'2': lambda: display_paginated_list("Top Directors", stats['top_directors']),
            '3': lambda: display_paginated_list("Top Actors", stats['top_actors']),'4': lambda: display_paginated_list("Top Countries", stats['top_countries']),
            '5': lambda: display_paginated_list("Movies by Decade", sorted_decades),'6': lambda: display_leaderboard("Highest Rated Movies", watched, 'rating'),
            '7': lambda: display_leaderboard("Lowest Rated Movies", watched, 'rating', sort_asc=True),'8': lambda: display_leaderboard("Longest Movies", watched, 'runtime'),
            '9': lambda: display_leaderboard("Shortest Movies", watched, 'runtime', sort_asc=True)}
        if choice in menu: menu[choice]()
        elif choice == 'b': break

# ==============================================================================
# --- FEATURE 4: SEARCH MOVIES ---
# ==============================================================================
def display_search_results(results, query):
    if not results:
        clear_screen(); print(colored(f"No results found for query: '{query}'", "yellow")); input("\nPress Enter..."); return
    page, page_size = 0, 15; total_pages = math.ceil(len(results) / page_size)
    while True:
        clear_screen(); print(colored(f"--- 🔎 Search Results for '{query}' ({len(results)} found) ---", "magenta", attrs=["bold"])); print(colored(f"Page {page + 1} of {total_pages}\n", "yellow"))
        start_index = page * page_size; end_index = start_index + page_size; current_page_movies = results[start_index:end_index]
        for i, movie in enumerate(current_page_movies, start=start_index): print(f"  {i+1:>3}. {movie.get('title', 'N/A')} ({movie.get('year', 'N/A')}) - dir. {movie.get('director', 'N/A')}")
        print("\n" + colored("[n]ext, [p]rev, [q]uit, or # to view details", "cyan")); choice = input("Navigation: ").lower()
        if choice == 'n' and page < total_pages - 1: page += 1
        elif choice == 'p' and page > 0: page -= 1
        elif choice == 'q': break
        else:
            try:
                choice_num = int(choice)
                if start_index < choice_num <= end_index:
                    selected_movie = results[choice_num - 1]
                    clear_screen(); print(colored(f"--- Details for: {selected_movie.get('title')} ---", "magenta"))
                    with open(selected_movie['filepath'], 'r', encoding='utf-8') as f: print(f.read())
                    input(colored("\nPress Enter to return...", "cyan"))
            except (ValueError, IndexError): pass

def run_search_menu(all_movies):
    while True:
        clear_screen(); print(colored("======= 🔎 MOVIE SEARCH =======", "green", attrs=["bold"])); print("Choose a method to search your collection.\n")
        print("  1. Search by Title"); print("  2. Search by Director"); print("  3. Search by Actor"); print("  4. Search by Year"); print("  5. Universal Keyword Search")
        print(colored("  b. Back to Main Menu", "red")); choice = input(colored("\nSelect a search method: ", "cyan")).lower()
        if choice == '1': query = input("Enter title: ").lower(); results = [m for m in all_movies if m.get('title') and query in m['title'].lower()]; display_search_results(results, query)
        elif choice == '2': query = input("Enter director: ").lower(); results = [m for m in all_movies if m.get('director') and query in m['director'].lower()]; display_search_results(results, query)
        elif choice == '3': query = input("Enter actor: ").lower(); results = [m for m in all_movies if any(a and query in a.lower() for a in m.get('actors', []))]; display_search_results(results, query)
        elif choice == '4': query = input("Enter year: "); results = [m for m in all_movies if str(m.get('year', 0)) == query]; display_search_results(results, query)
        elif choice == '5':
            query = input("Enter keyword: ").lower(); results = []; seen_titles = set()
            for movie in all_movies:
                if movie.get('title') in seen_titles: continue
                match = any([movie.get('title') and query in movie.get('title','').lower(), movie.get('director') and query in movie.get('director','').lower(), any(g and query in g.lower() for g in movie.get('genres',[])), any(a and query in a.lower() for a in movie.get('actors',[]))])
                if match: results.append(movie); seen_titles.add(movie.get('title'))
            display_search_results(results, query)
        elif choice == 'b': break

# ==============================================================================
# --- MAIN MENU ---
# ==============================================================================
def main_menu():
    all_movies = load_movie_data()
    while True:
        clear_screen(); print(colored("======= MOVIELOG CLI =======", "green", attrs=["bold"])); print(f"Your personal movie logger. ({len(all_movies)} movies loaded)\n")
        print("  1. ✍️  Log a New Movie"); print("  2. 📚  Browse 'To-Watch' List"); print("  3. 📊  View Stats Dashboard"); print("  4. 🔎  Search Movies")
        print(colored("  q. 👋  Quit", "red")); choice = input(colored("\nWhat would you like to do? ", "cyan")).lower()
        if choice == '1': run_movie_logger(); all_movies = load_movie_data()
        elif choice == '2': run_browse_list()
        elif choice == '3': run_stats_viewer()
        elif choice == '4': run_search_menu(all_movies)
        elif choice == 'q': print(colored("Happy movie watching!", "green")); break

if __name__ == "__main__":
    main_menu()