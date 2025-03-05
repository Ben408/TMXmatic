import requests
import os
from config import XO_TMX_PATH, ensure_dir

# Replace these with your actual credentials and TM ID
username = 'ben.cornelius2'
password = 'tacoTAC0truck!'
tm_id = '0W3AcG1ODAJL09FKgnDMJg'
# The TM id is the last part of the URL when looking at the TM in the TMS UI

# Step 1: Authenticate and get the access token
auth_url = 'https://cloud.memsource.com/web/api2/v1/auth/login'
auth_payload = {
    'userName': username,
    'password': password
}

try:
    auth_response = requests.post(auth_url, json=auth_payload)
    auth_response.raise_for_status()
    token = auth_response.json()['token']
    print("Authentication successful!")
except requests.exceptions.HTTPError as err:
    print(f"HTTP error occurred: {err}")
    print(f"Response content: {auth_response.content}")
    exit(1)
except Exception as err:
    print(f"An error occurred: {err}")
    exit(1)

# Step 2: List all project templates
templates_url = 'https://cloud.memsource.com/web/api2/v1/projectTemplates'
headers = {
    'Authorization': f'Bearer {token}'
}

try:
    templates_response = requests.get(templates_url, headers=headers)
    templates_response.raise_for_status()
    templates = templates_response.json()['content']
except requests.exceptions.HTTPError as err:
    print(f"HTTP error occurred: {err}")
    print(f"Response content: {templates_response.content}")
    exit(1)
except Exception as err:
    print(f"An error occurred: {err}")
    exit(1)

# Step 3: Filter templates by Translation Memory
filtered_templates = [template for template in templates if tm_id in [tm['id'] for tm in template['translationMemories']]]

# Step 4: Download TMX files for filtered templates
download_url = 'https://cloud.memsource.com/web/api2/v1/transMemories/{}/export'

ensure_dir(XO_TMX_PATH)

for template in filtered_templates:
    template_id = template['id']
    template_name = template['name']
    
    try:
        download_response = requests.get(download_url.format(tm_id), headers=headers)
        download_response.raise_for_status()
        
        filename = f"{template_name}_{template_id}.tmx"
        file_path = os.path.join(XO_TMX_PATH, filename)
        
        with open(file_path, 'wb') as f:
            f.write(download_response.content)
        
        print(f"Downloaded TMX for template: {template_name} (ID: {template_id})")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred while downloading TMX for template {template_name}: {err}")
    except Exception as err:
        print(f"An error occurred while downloading TMX for template {template_name}: {err}")

print("TMX download process completed.")