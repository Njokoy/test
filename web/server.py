from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import os
import time

app = Flask(__name__)

# Configuration dynamique via les variables d'environnement
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}"
    f"@{os.environ['DATABASE_HOST']}:3306/{os.environ['DATABASE_NAME']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def wait_for_db():
    attempts = 0
    while attempts < 5:
        try:
            db.session.execute(text('SELECT 1'))
            return True
        except Exception as e:
            print(f"Database connection failed ({attempts}/5): {e}")
            time.sleep(5)
            attempts += 1
    return False

def get_movies():
    movies = []
    try:
        if not wait_for_db():
            raise Exception("Could not connect to database")
        
        result = db.session.execute(text("SELECT * FROM movies LIMIT 8"))
        for row in result:
            movies.append({"name": row[0], "rating": row[1]})
        print(f"Films récupérés : {movies}")  # Log des films récupérés
    except Exception as e:
        print(f"Erreur lors de la récupération des films : {str(e)}")
    return movies

@app.route('/')
def index():
    movies = get_movies()
    movies_html = "<div class='movie-list'>"
    for movie in movies:
        movies_html += f"""
        <div class='movie-card'>
            <h3>{movie['name']}</h3>
            <p>Note : <span class='rating'>{movie['rating']}</span></p>
        </div>
        """
    movies_html += "</div>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Liste des Films</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f9;
                color: #333;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                flex-direction: column;
            }}
            h1 {{
                color: #444;
                margin-bottom: 20px;
            }}
            .movie-list {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                max-width: 800px;
                width: 100%;
            }}
            .movie-card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .movie-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }}
            .movie-card h3 {{
                margin: 0;
                font-size: 1.5em;
                color: #555;
            }}
            .movie-card p {{
                margin: 10px 0 0;
                font-size: 1.1em;
                color: #777;
            }}
            .rating {{
                font-weight: bold;
                color: #ff6f61;
            }}
        </style>
    </head>
    <body>
        <h1>Liste des Films</h1>
        {movies_html}
    </body>
    </html>
    """
    return render_template_string(html_content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)