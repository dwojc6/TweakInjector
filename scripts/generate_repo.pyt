import json
import yaml
import os
from datetime import datetime

CONFIG_PATH = "config/apps.yml"
OUTPUT_DIR = "docs"
REPO_JSON_PATH = os.path.join(OUTPUT_DIR, "repo.json")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    repo_data = {
        "name": "Slowie's IPA Repo",
        "identifier": "com.github.actions.repo",
        "apps": []
    }

    for app in config['apps']:
        if not app.get('download_url'):
            continue
            
        repo_entry = {
            "name": app['name'],
            "bundleIdentifier": app['bundle_id'],
            "version": app['current_version'],
            "downloadURL": app['download_url'],
            "developerName": "Tweaked",
            "iconURL": app.get('icon_url', "https://via.placeholder.com/150"), # Add icon URLs to yaml if desired
            "localizedDescription": f"Auto-injected via GitHub Actions. Last update: {datetime.now().strftime('%Y-%m-%d')}",
            "size": 100000000 # Optional: You can track file size in process_apps.py
        }
        repo_data['apps'].append(repo_entry)

    with open(REPO_JSON_PATH, 'w') as f:
        json.dump(repo_data, f, indent=2)
    
    print(f"Repo generated with {len(repo_data['apps'])} apps.")

if __name__ == "__main__":
    main()
