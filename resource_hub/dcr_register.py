import httpx
import json
import os

DCR_ENDPOINT = "http://localhost:8000/auth/dcr/register"

payload = {
    "client_name": "cenrixa-resource-hub",
    "redirect_uris": ["http://127.0.0.1:8001/auth/callback"],
    "response_types": ["code"],
    "grant_types": ["authorization_code"]
}

def register_app():
    print("Initiating Dynamic Client Registration (DCR) for Resource Hub...")
    try:
        response = httpx.post(DCR_ENDPOINT, json=payload)
        
        if response.status_code in [200, 201]:
            data = response.json()
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")
            
            # Save to .env
            with open(".env", "w") as f:
                f.write(f"CLIENT_ID={client_id}\n")
                f.write(f"CLIENT_SECRET={client_secret}\n")
                f.write('KEYCLOAK_URL="http://localhost:8000"\n')
                
            print(f"Success! App registered with Client ID: {client_id}")
            print("Credentials saved to .env file.")
        else:
            print(f"Failed to register. Status: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print("Error during DCR:")
        print(str(e))
        print("Note: Make sure your central Keycloak/BAAS server is running on port 8000.")

if __name__ == "__main__":
    register_app()
