import os
import yaml
import requests
import subprocess
import shutil

# Config
CONFIG_PATH = "config/apps.json"
BUILD_DIR = "build_temp"
PIXELDRAIN_KEY = os.environ.get("PIXELDRAIN_API_KEY")

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_config(data):
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(data, f, sort_keys=False)

def get_latest_github_release(repo, asset_regex):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, None
    data = resp.json()
    for asset in data.get('assets', []):
        if asset_regex in asset['name']:
            return asset['browser_download_url'], data['tag_name']
    return None, None

def upload_to_pixeldrain(file_path, filename):
    if not PIXELDRAIN_KEY:
        print("Skipping upload (No API Key)")
        return "https://pixeldrain.com/u/EXAMPLE"
    
    url = "https://pixeldrain.com/api/file"
    auth = requests.auth.HTTPBasicAuth('', PIXELDRAIN_KEY)
    with open(file_path, 'rb') as f:
        files = {'file': (filename, f)}
        resp = requests.post(url, auth=auth, files=files)
        
    if resp.status_code == 201:
        file_id = resp.json()['id']
        return f"https://pixeldrain.com/u/{file_id}"
    return None

def main():
    config = load_config()
    os.makedirs(BUILD_DIR, exist_ok=True)
    
    for app in config['apps']:
        print(f"Checking {app['name']}...")
        
        # 1. Check if we need to update
        # (Simplified logic: In a real scenario, you'd check AppStore API here like your old script)
        # For now, we assume if we find a new Deb or if Force Update is on, we go.
        
        tweaks_to_download = []
        should_build = os.environ.get("FORCE_UPDATE") == 'true'
        
        for tweak in app.get('tweaks', []):
            if tweak['type'] == 'github_release':
                url, version = get_latest_github_release(tweak['repo'], tweak['asset_regex'])
                # You could compare 'version' to a stored 'last_tweak_version' here
                if url:
                    tweaks_to_download.append(url)
                    should_build = True 
            elif tweak['type'] == 'direct':
                tweaks_to_download.append(tweak['url'])

        if not should_build:
            print(f"No updates for {app['name']}")
            continue

        print(f"Building {app['name']}...")
        
        # 2. Download IPA
        ipa_path = os.path.join(BUILD_DIR, "source.ipa")
        
        if app.get('ipa_source'):
            # Direct HTTP Download
            print(f"Downloading from URL: {app['ipa_source']}")
            with requests.get(app['ipa_source'], stream=True) as r:
                with open(ipa_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
        elif app.get('app_store_url'):
            # Telegram Download
            print(f"Requesting decryption from Telegram for {app['name']}...")
            env = os.environ.copy()
            # Ensure these are passed from the workflow
            cmd = ["python3", "scripts/fetch_ipa.py", app['app_store_url']]
            try:
                subprocess.run(cmd, check=True, env=env)
            except subprocess.CalledProcessError:
                print(f"❌ Telegram download failed for {app['name']}")
                continue
        else:
            print("No IPA source or App Store URL provided.")
            continue
            
        if not os.path.exists(ipa_path):
             print("IPA file missing after download step.")
             continue

        # 3. Gather Tweaks (Download or Copy Local)
        deb_files = []
        
        # We need to look at the config's tweak list for this specific app
        for i, tweak in enumerate(app.get('tweaks', [])):
            
            # Define where we want the file to end up for injection
            dest_filename = f"tweak_{i}.deb"
            dest_path = os.path.join(BUILD_DIR, dest_filename)
            
            if tweak['type'] == 'github_release':
                url, version = get_latest_github_release(tweak['repo'], tweak['asset_regex'])
                if url:
                    print(f"   ⬇️ Downloading {tweak['repo']}...")
                    with requests.get(url, stream=True) as r:
                        with open(dest_path, 'wb') as f:
                            shutil.copyfileobj(r.raw, f)
                    deb_files.append(dest_path)
                else:
                    print(f"   ⚠️ Could not find release for {tweak['repo']}")

            elif tweak['type'] == 'direct':
                print(f"   ⬇️ Downloading direct file...")
                with requests.get(tweak['url'], stream=True) as r:
                    with open(dest_path, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                deb_files.append(dest_path)

            elif tweak['type'] == 'local':
                # Handle local file from repo
                local_source = tweak['path'] # e.g., "debs/Rocket.deb"
                
                if os.path.exists(local_source):
                    print(f"   📂 Using local file: {local_source}")
                    shutil.copy(local_source, dest_path)
                    deb_files.append(dest_path)
                else:
                    print(f"   ❌ Local file not found: {local_source}")
                    # You might want to exit or skip here depending on strictness
            
        if not deb_files:
            print("   ⚠️ No tweaks found to inject. Skipping...")
            continue

        # 4. Inject
        output_ipa = os.path.join(BUILD_DIR, "injected.ipa")
        # Azule command: azule -i input.ipa -o output.ipa -f tweak1.deb tweak2.deb
        cmd = ["azule", "-i", ipa_path, "-o", output_ipa, "-f"] + deb_files
        subprocess.run(cmd, check=True)

        # 5. Upload
        download_url = upload_to_pixeldrain(output_ipa, f"{app['name']}_Tweaked.ipa")
        
        if download_url:
            app['download_url'] = download_url
            print(f"Uploaded to {download_url}")

        # Cleanup for next app
        shutil.rmtree(BUILD_DIR)
        os.makedirs(BUILD_DIR, exist_ok=True)

    save_config(config)

if __name__ == "__main__":
    main()
