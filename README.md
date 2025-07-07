# MovieLog CLI

**MovieLog CLI** is a powerful command-line interface for building and managing a personal, offline movie database. Take full ownership of your viewing history, track what you want to watch, and explore detailed statistics about your habits—all from the comfort of your terminal.

This system is built to be private, free, open-source, and highly customizable. It uses plain Markdown files to store your data, making it future-proof and easy to manage.

![Screenshot of the CLI](https://i.imgur.com/your-screenshot-url.png) <!-- Suggestion: Take a screenshot of your CLI in action and upload to imgur -->

## ✨ Features

- **Log Movies via Command Line:** A user-friendly interface to search for and log movies.
- **Automated Data Fetching:** Pulls movie details (director, genre, runtime, etc.) automatically from [The Movie Database (TMDB)](https://www.themoviedb.org/).
- **100% Offline and Private:** Your data lives in Markdown files on your local machine. No servers, no tracking.
- **Powerful Statistics Dashboard:** Get detailed insights into your viewing habits, including top directors, genres, and rating distributions.
- **Excel Migration:** A dedicated script to import your existing viewing history from an Excel file.
- **Obsidian Integration:** Comes with a template for a beautiful and dynamic dashboard using the [Obsidian](https://obsidian.md/) note-taking app.

---

## 🚀 Getting Started

Follow these steps to set up your own MovieLog CLI.

### Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- A free API key from [The Movie Database (TMDB)](https://www.themoviedb.org/signup).

### 1. Installation

First, clone the repository to your local machine.

````bash
git clone https://github.com/your-username/movielog-cli.git
cd movielog-cli```

Next, it's highly recommended to create a Python virtual environment to keep dependencies isolated.

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate

# Activate it (macOS/Linux)
source venv/bin/activate
````

Now, install the required packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 2. Configuration

The script needs your TMDB API key to function.

1.  Create a file named `.env` in the root of the project directory.
2.  Copy the contents of `.env.example` into your new `.env` file.
3.  Replace `"YOUR_API_KEY_GOES_HERE"` with your actual TMDB API key.

The `.env` file is listed in `.gitignore`, so your secret key will never be uploaded to GitHub.

---

## ⚙️ Usage

To run the application, simply execute the `movielog_cli.py` script from your terminal.

```bash
python movielog_cli.py
```

You will be greeted with a main menu that allows you to:

- **Log a New Movie:** Search for a movie and add it to your database.
- **Browse 'To-Watch' List:** View a paginated list of all movies marked "to-watch."
- **View Stats Dashboard:** See detailed analytics of your watched movies.
- **Search Movies:** Search your local collection by title, director, actor, and more.

---

## 💾 Migrating from Excel

If you have an existing movie list in an Excel file, you can use the `migrate_from_excel.py` script to import it.

1.  Place your Excel file in the root of the project directory and name it `movies.xlsx`.
2.  **Important:** Ensure your file has columns named `Names` (for the movie title and year, e.g., "Parasite (2019)") and `Status` (with the text "watched" for movies you've seen).
3.  Run the migration script:
    `bash
    python migrate_from_excel.py
    `
    This script will read each row, search for the movie on TMDB, and create a corresponding Markdown file in the `movies` folder.

---

## 📊 The Obsidian Dashboard

While the CLI is great for data entry and stats, [Obsidian](https://obsidian.md/) provides a beautiful way to visualize your collection.

1.  Download and install Obsidian.
2.  Use the "Open folder as vault" option and select your `movielog-cli` folder.
3.  In Obsidian's settings, go to **Community Plugins**, turn them on, and install the **Dataview** plugin.
4.  Create a new note in Obsidian named `_Movie Dashboard.md`.
5.  Copy the code below into that note.

### Dashboard Code

````markdown
# Movie Dashboard

## 🎬 To-Watch List

_A list of all the movies you want to watch, sorted by year._

` ```dataview `
TABLE director, year, join(genres) as "Genres"
FROM "movies"
WHERE status = "to-watch"
SORT year ASC
` ``` `

## ⭐ My Top Rated Movies

_Your highest-rated films._

` ```dataview `
TABLE director, year, rating, join(genres) as "Genres"
FROM "movies"
WHERE rating > 8
SORT rating DESC
` ``` `

## ⏰ Recently Watched

_The last 10 movies you've logged as watched._

` ```dataview `
TABLE director, rating, date_watched as "Date Watched"
FROM "movies"
WHERE status = "watched" AND date_watched
SORT date_watched DESC
LIMIT 10
` ``` `

## 🎥 Favorite Directors

_A count of how many films you've seen by each director._

` ```dataview `
TABLE rows.length as "Count"
FROM "movies"
WHERE director != "Unknown" AND status="watched"
GROUP BY director
SORT rows.length DESC
LIMIT 15
` ``` `
````

_(Note: I had to add spaces to the dataview backticks above to display them correctly. In your actual file, they should be ` ```dataview `)_

Obsidian will now display dynamic, sortable tables of your movie collection that automatically update whenever you add a new file!
