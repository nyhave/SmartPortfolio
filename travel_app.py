import urllib.request
import urllib.parse
import re
import sqlite3
from dataclasses import dataclass
from typing import List

DB_NAME = 'travel.db'

@dataclass
class Suggestion:
    title: str
    link: str

class TravelDB:
    def __init__(self, db_name: str = DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination TEXT,
                start_date TEXT,
                end_date TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                title TEXT,
                link TEXT,
                FOREIGN KEY(trip_id) REFERENCES trips(id)
            )
            """
        )
        self.conn.commit()

    def add_trip(self, destination: str, start_date: str, end_date: str, suggestions: List[Suggestion]):
        cur = self.conn.cursor()
        cur.execute(
            'INSERT INTO trips (destination, start_date, end_date) VALUES (?, ?, ?)',
            (destination, start_date, end_date)
        )
        trip_id = cur.lastrowid
        for s in suggestions:
            cur.execute(
                'INSERT INTO suggestions (trip_id, title, link) VALUES (?, ?, ?)',
                (trip_id, s.title, s.link)
            )
        self.conn.commit()

    def fetch_trips(self):
        cur = self.conn.cursor()
        cur.execute('SELECT id, destination, start_date, end_date FROM trips')
        trips = cur.fetchall()
        result = []
        for trip in trips:
            cur.execute('SELECT title, link FROM suggestions WHERE trip_id=?', (trip[0],))
            suggestions = cur.fetchall()
            result.append({'id': trip[0], 'destination': trip[1], 'start_date': trip[2], 'end_date': trip[3],
                           'suggestions': [{'title': s[0], 'link': s[1]} for s in suggestions]})
        return result

    def close(self):
        self.conn.close()


def search_google(query: str, num_results: int = 5) -> List[Suggestion]:
    url = 'https://www.google.com/search?hl=en&q=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html)
        links = re.findall(r'<a href="/url\?q=(.*?)&', html)
        suggestions = []
        for title, link in zip(titles, links)[:num_results]:
            clean_title = re.sub('<.*?>', '', title)
            suggestions.append(Suggestion(clean_title, urllib.parse.unquote(link)))
        return suggestions
    except Exception as e:
        # If Google cannot be reached (common in restricted environments), return a placeholder
        return [Suggestion(f'Unable to fetch from Google: {e}', '')]


def demo_madrid_trip():
    db = TravelDB()
    query = 'Madrid travel 26-28 September 2025'
    suggestions = search_google(query)
    db.add_trip('Madrid', '2025-09-26', '2025-09-28', suggestions)
    trips = db.fetch_trips()
    for trip in trips:
        print(f"Trip to {trip['destination']} from {trip['start_date']} to {trip['end_date']}")
        for s in trip['suggestions']:
            print(f"  - {s['title']} ({s['link']})")
    db.close()

if __name__ == '__main__':
    demo_madrid_trip()
