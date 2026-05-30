
import os
import sys
import json
import sqlite3
import shutil
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def convert_prtime(pr_time):
    if not pr_time:
        return None
    try:
        dt = datetime.fromtimestamp(int(pr_time) / 1000000.0, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return str(pr_time)

def get_base_path():
    env_base_path = os.environ.get("FIREFOX_PROFILES_PATH")
    if env_base_path:
        return os.path.expanduser(env_base_path)

    if sys.platform == "darwin":
        path = "~/Library/Application Support/Firefox/Profiles"
    elif sys.platform == "win32":
        path = "~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles"
    else:
        path = "~/.mozilla/firefox"
    return os.path.expanduser(path)

def resolve_active_profile():
    env_profile_path = os.environ.get("FIREFOX_PROFILE_PATH")
    if env_profile_path:
        profile_path = os.path.expanduser(env_profile_path)
        places_path = os.path.join(profile_path, "places.sqlite")
        if os.path.exists(places_path):
            print(f"Using Firefox profile from FIREFOX_PROFILE_PATH: {profile_path}")
            return profile_path

        print(f"FIREFOX_PROFILE_PATH does not contain places.sqlite: {profile_path}")
        return None

    base_path = get_base_path()
    if not os.path.exists(base_path):
        print("Base path not found for Firefox")
        return None

    profiles = []
    try:
        for d in os.listdir(base_path):
            dir_path = os.path.join(base_path, d)
            if os.path.isdir(dir_path):
                places_path = os.path.join(dir_path, "places.sqlite")
                if os.path.exists(places_path):
                    mtime = os.path.getmtime(places_path)
                    profiles.append((dir_path, mtime))
    except Exception as e:
        print(f"Error accessing profiles: {e}")
        return None

    if not profiles:
        return None

    profiles.sort(key=lambda x: x[1], reverse=True)
    best_match = profiles[0][0]
    print(f"Resolved active profile: {best_match}")
    return best_match

def query_sqlite(db_name, profile_path, query):
    original_path = os.path.join(profile_path, db_name)
    if not os.path.exists(original_path):
        return []
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, db_name)
    
    for ext in ["", "-wal", "-shm"]:
        src = original_path + ext
        if os.path.exists(src):
            shutil.copy2(src, temp_path + ext)
            
    results = []
    try:
        conn = sqlite3.connect(temp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        for row in cursor.fetchall():
            results.append(dict(row))
        conn.close()
    except Exception as e:
        print(f"SQLite Error reading {db_name}: {e}")
    finally:
        shutil.rmtree(temp_dir)
    return results

def extract_bookmarks(profile_path):
    q = """
    SELECT b.id, b.title, p.url, b.dateAdded as date_added, b.type 
    FROM moz_bookmarks b 
    LEFT JOIN moz_places p ON b.fk = p.id 
    WHERE b.title IS NOT NULL AND b.title != ''
    """
    results = query_sqlite("places.sqlite", profile_path, q)
    for r in results:
        r["date_added"] = convert_prtime(r["date_added"])
        r["type"] = "folder" if r["type"] == 2 else "url"
    return results

def extract_history(profile_path):
    q = "SELECT id, url, title, visit_count, last_visit_date FROM moz_places WHERE visit_count > 0 ORDER BY last_visit_date DESC LIMIT 5000"
    results = query_sqlite("places.sqlite", profile_path, q)
    for r in results:
        r["last_visit_date"] = convert_prtime(r["last_visit_date"])
    return results

def extract_top_sites(profile_path):
    q = "SELECT url, title FROM moz_places WHERE frecency > 0 ORDER BY frecency DESC LIMIT 100"
    results = query_sqlite("places.sqlite", profile_path, q)
    for index, row in enumerate(results, start=1):
        row["url_rank"] = index
    return results

def extract_extensions(profile_path):
    ext_path = os.path.join(profile_path, "extensions.json")
    if not os.path.exists(ext_path): 
        return []
    
    results = []
    try:
        with open(ext_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for addon in data.get("addons", []):
            if addon.get("type") == "extension":
                name = addon.get("defaultLocale", {}).get("name") or addon.get("name", "")
                results.append({
                    "id": addon.get("id", ""),
                    "name": name,
                    "version": addon.get("version", "")
                })
    except Exception as e:
        print(f"Error parsing extensions: {e}")
    return results

class BrowserAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path).path
        path_parts = parsed_path.strip("/").split("/")
        
        if len(path_parts) == 2 and path_parts[0] == "firefox":
            data_type = path_parts[1]
            profile_path = resolve_active_profile()
            
            if not profile_path:
                self.send_success({"data": []})
                return
                
            funcs = {
                "bookmarks": extract_bookmarks, 
                "history": extract_history,
                "top_sites": extract_top_sites,
                "extensions": extract_extensions
            }
            
            if data_type in funcs:
                data = funcs[data_type](profile_path)
                self.send_success({"data": data})
                return
        
        self.send_response(404)
        self.end_headers()
        
    def send_success(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    port = 8766
    server = ThreadingHTTPServer(("127.0.0.1", port), BrowserAPIHandler)
    print(f"Starting Firefox local server on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()
        sys.exit(0)
