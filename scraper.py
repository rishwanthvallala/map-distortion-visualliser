import requests
from bs4 import BeautifulSoup
import pprint

def scrape_proj_list():
    """
    Scrapes the PROJ documentation to get a list of all projection codes.
    """
    url = "https://proj.org/operations/projections/index.html"
    
    try:
        print("Fetching data from the website...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print("Successfully fetched data.")
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch the URL. {e}")
        print("Please check your internet connection.")
        return

    print("Parsing the list of projections...")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    main_content = soup.find('body')
    if not main_content:
        print("Error: Could not find the main content section of the page.")
        return

    projection_list = main_content.find('ul')
    if not projection_list:
        print("Error: Could not find the projection list (<ul>) in the main content.")
        return
        
    projections_to_show = {}

    for item in projection_list.find_all('li'):
        code_tag = item.find('code')
        
        if code_tag:
            short_code = code_tag.text.strip()
            full_text = item.text.strip()
            parts = full_text.split('–', 1)
            
            if len(parts) > 1:
                long_name = parts[1].strip()
                proj_string = f"+proj={short_code} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
                projections_to_show[long_name] = proj_string
            else:
                print(f"Warning: Could not parse full text for code '{short_code}'. Skipping this entry.")
        else:
            print("Warning: No <code> tag found in this list item. Skipping this entry.")

    print("\n--- SCRAPING COMPLETE ---")
    print("Copy the following dictionary into your main script:\n")
    
    # Print the result in a copy-paste-friendly format
    print("projections_to_show = \\")
    pprint.pprint(projections_to_show, indent=2)

if __name__ == "__main__":
    scrape_proj_list()