"""My Festival REST API — M10 starter (CSC Rahti).

FI: Tämä on M10-tehtävän lähtöpohja. GET /api/artists on valmiina mallina;
    toteuta loput TODO-kohdat. Aja paikallisesti:  python app.py
    ja testaa:  python test_endpoints.py http://localhost:8080
EN: This is the M10 starter. GET /api/artists is done as an example;
    implement the remaining TODOs. Run locally:  python app.py
    and test:  python test_endpoints.py http://localhost:8080
"""
import os
import sqlite3

from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)

# FI: Kanta kulkee kontin mukana. Polun voi vaihtaa ympäristömuuttujalla.
# EN: The database ships inside the container. Override the path with an env var.
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "myfestival.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # M8: sqlite3 ei valvo FK:ita oletuksena / FKs are off by default
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    """FI: Rahti ja selain näkevät, että sovellus on pystyssä.
    EN: Lets Rahti and your browser see the app is up."""
    return jsonify(status="ok", endpoints=["/api/artists", "/api/days", "/api/stages",
                                           "/api/artists/<id>/events", "/api/timetable?day=YYYY-MM-DD",
                                           "POST /api/events", "DELETE /api/events/<id>"])


@app.get("/api/artists")
def get_artists():
    conn = get_db()
    rows = conn.execute("SELECT artist_id, name, country FROM Artist ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/days")
def get_days():
    """FI: Apuendpoint: festivaalipäivät (tarkistin hakee tästä day_id:n).
    EN: Helper endpoint: festival days (the checker reads day_id from here)."""
    conn = get_db()
    rows = conn.execute("SELECT day_id, date FROM Day ORDER BY date").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/stages")
def get_stages():
    """FI: Apuendpoint: lavat. EN: Helper endpoint: stages."""
    conn = get_db()
    rows = conn.execute("SELECT stage_id, name FROM Stage ORDER BY stage_id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/artists/<int:artist_id>/events")
def get_artist_events(artist_id):
    # TODO FI: palauta artistin esiintymiset: event_id, day, stage, starts. Tuntematon id → 404.
    # TODO EN: return the artist's performances: event_id, day, stage, starts. Unknown id → 404.
    conn = get_db()
    artist = conn.execute("SELECT * FROM Artist WHERE artist_id = ?", (artist_id,)).fetchone()
    if (artist is None):
        return jsonify(error = "Unknown id"), 404
    rows = conn.execute(
        "SELECT event_id, date, Stage.name, start_dt FROM event JOIN Day USING(day_id) JOIN Stage USING(stage_id) WHERE artist_id = ?",
        (artist_id, )
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/timetable")
def get_timetable():
    day = request.args.get("day")  # FI: kyselyparametri ?day=2025-07-05 / EN: query parameter
    # TODO FI: rivit {date, stage, artist, starts, ends} aikajärjestyksessä. Ilman parametria koko ohjelma,
    #          virheellinen päivämäärä → 400. Parametrisoi kysely!
    # TODO EN: rows {date, stage, artist, starts, ends} in time order. No parameter → whole program,
    #          invalid date → 400. Parameterize the query!

    conn = get_db()

    if day:
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            return jsonify(error="Invalid date format. Use YYYY-MM-DD."), 400

        rows = conn.execute(
            "SELECT date, stage, artist, starts, ends FROM V_Schedule WHERE date = ? ORDER BY date, starts",
            (day,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT date, stage, artist, starts, ends FROM V_Schedule ORDER BY date, starts"
        ).fetchall()

    conn.close()
    return jsonify([dict(row) for row in rows])


@app.post("/api/events")
def create_event():
    body = request.get_json(silent=True) or {}
    # TODO FI: tarkista kentät artist_id, stage_id, day_id, start_dt → puuttuu = 400.
    #          Lisää rivi Event-tauluun (event_type 'performance', kesto esim. 45 min).
    #          sqlite3.IntegrityError (esim. olematon artist_id) → 400 ja selkeä virheviesti.
    #          Onnistuminen → 201 ja uuden rivin tiedot JSONina (sis. event_id).
    # TODO EN: validate artist_id, stage_id, day_id, start_dt → missing = 400.
    #          Insert into Event (event_type 'performance', duration e.g. 45 min).
    #          sqlite3.IntegrityError (e.g. unknown artist_id) → 400 with a clear message.
    #          Success → 201 with the new row as JSON (incl. event_id).

    required = ["artist_id", "stage_id", "day_id", "start_dt"]

    missing = [field for field in required if field not in body]
    if missing:
        return jsonify(
            error=f"Missing required fields: {', '.join(missing)}"
        ), 400

    try:
        start_dt = datetime.fromisoformat(body["start_dt"])
    except (TypeError, ValueError):
        return jsonify(error="Invalid start_dt format"), 400

    duration = 45
    end_dt = start_dt + timedelta(minutes=duration)

    conn = get_db()

    try:
        event_type = conn.execute(
            "SELECT event_type_id FROM EventType WHERE code = ?",
            ("performance",)
        ).fetchone()

        if event_type is None:
            return jsonify(error="Event type 'performance' not found"), 400

        cursor = conn.execute(
            "INSERT INTO Event (event_type_id, day_id, stage_id, artist_id, start_dt, end_dt, duration_min) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_type["event_type_id"],
                body["day_id"],
                body["stage_id"],
                body["artist_id"],
                start_dt.isoformat(sep=" "),
                end_dt.isoformat(sep=" "),
                duration,
            ),
        )
        conn.commit()
        event_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM Event WHERE event_id = ?",
            (event_id,)
        ).fetchone()

        return jsonify(dict(row)), 201

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify(error=f"Database constraint violation: {str(e)}"), 400

    finally:
        conn.close()


@app.delete("/api/events/<int:event_id>")
def delete_event(event_id):
    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM Event WHERE event_id = ?",
        (event_id,)
    )

    conn.commit()

    if cursor.rowcount == 0:
        return jsonify(error="Event not found"), 404

    conn.close()

    return "", 204



if __name__ == "__main__":
    # FI: Paikallinen kehityspalvelin. Rahdissa sovellusta ajaa gunicorn (ks. Dockerfile).
    # EN: Local dev server. On Rahti the app is run by gunicorn (see Dockerfile).
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
