import requests
from bs4 import BeautifulSoup
import re
import json
import sys

# --- Configuration ---
HTML_FILE_PATH = 'index.html' # Assuming the immersive HTML is saved as index.html
REQUEST_TIMEOUT = 10 # seconds
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def extract_urls_from_js(file_path):
    """
    Parses the HTML file to find the 'institutes' and 'jobBoards' JavaScript arrays
    and extracts all 'url' and 'homepageUrl' values.
    """
    print(f"--- Parsing HTML file: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)

    urls = set() # Use a set to avoid duplicate URLs

    # Regular expression to find JavaScript arrays (institutes and jobBoards)
    # This is a bit brittle but avoids needing a full JS parser.
    js_array_pattern = re.compile(r'const\s+(institutes|jobBoards)\s*=\s*(\[.*?\]);', re.DOTALL | re.MULTILINE)
    
    found_arrays = js_array_pattern.findall(html_content)

    if not found_arrays:
        print("Error: Could not find 'institutes' or 'jobBoards' JavaScript arrays in the HTML file.")
        sys.exit(1)

    print(f"Found {len(found_arrays)} data array(s) in the script tag.")

    for array_name, array_content in found_arrays:
        try:
            # Clean up the JS for JSON parsing: remove trailing commas, use double quotes.
            # This is a simplification and might fail on more complex JS objects.
            json_str = array_content.replace("'", '"').replace('`', '"')
            # Remove trailing commas from objects `... ,}` -> `...}`
            json_str = re.sub(r',\s*}', '}', json_str)
            # Remove trailing commas from arrays `... ,]` -> `...]`
            json_str = re.sub(r',\s*\]', ']', json_str)

            data = json.loads(json_str)

            for item in data:
                if 'url' in item and item['url']:
                    urls.add(item['url'])
                if 'homepageUrl' in item and item['homepageUrl']:
                    urls.add(item['homepageUrl'])
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse the '{array_name}' array. It might not be valid JSON.")
            print(f"Error details: {e}")
            continue

    print(f"--- Found {len(urls)} unique URLs to check ---")
    return list(urls)

def check_link(url, session):
    """
    Checks a single URL for a valid response.
    Returns a status string: 'OK' or an error message.
    """
    try:
        headers = {'User-Agent': USER_AGENT}
        response = session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, headers=headers)
        
        # Check for client or server errors (4xx or 5xx)
        if response.status_code >= 400:
            return f"FAILED: Status {response.status_code}"
        else:
            return "OK"
    except requests.exceptions.RequestException as e:
        # Catches connection errors, timeouts, etc.
        return f"FAILED: Request Error ({e.__class__.__name__})"
    except Exception as e:
        return f"FAILED: An unexpected error occurred ({e})"

def main():
    """
    Main function to run the link checker.
    """
    urls_to_check = extract_urls_from_js(HTML_FILE_PATH)
    if not urls_to_check:
        print("No URLs found to check. Exiting.")
        return

    broken_links = []
    
    # Use a session object for connection pooling
    with requests.Session() as session:
        for i, url in enumerate(urls_to_check):
            print(f"Checking ({i+1}/{len(urls_to_check)}): {url}")
            status = check_link(url, session)
            if status != "OK":
                broken_links.append((url, status))
                print(f"  -> {status}")
            else:
                print("  -> OK")


    print("\n--- Link Check Complete ---")
    if not broken_links:
        print("✅ All links are working correctly!")
    else:
        print(f"🚨 Found {len(broken_links)} broken links:")
        for url, reason in broken_links:
            print(f"  - {url} ({reason})")
        # Exit with a non-zero status code to make the GitHub Action fail
        sys.exit(1)

if __name__ == "__main__":
    main()
