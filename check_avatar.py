import requests
import json

# REPLACE WITH YOUR KEY
HEYGEN_API_KEY = "sk_V2_hgu_ktnQdm1avGm_ezvg7zsGoEVlGKbKrmJs6iaJCfDmNFw0"

url = "https://api.heygen.com/v2/avatars"

headers = {
    "X-Api-Key": HEYGEN_API_KEY,
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        avatars = data.get('data', {}).get('avatars', [])
        
        print(f"✅ Found {len(avatars)} available avatars.\n")
        print("--- TOP 5 VALID AVATAR IDs ---")
        for i, avatar in enumerate(avatars[:5]):
            print(f"Name: {avatar.get('name')}")
            print(f"ID:   {avatar.get('avatar_id')}")
            print("----------------------------")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Error: {e}")