import requests
from config.config import settings

def update_webhook():
    print("Updating Evolution API Webhook to use internal network...")
    
    # 172.17.0.1 is the default internal IP that lets Docker containers talk to the host machine
    WEBHOOK_URL = "http://172.17.0.1:8001/webhook/evolution"
    url = f"{settings.EVOLUTION_API_URL}/webhook/set/{settings.EVOLUTION_INSTANCE_NAME}"
    
    headers = {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "webhook": {
            "enabled": True,
            "url": WEBHOOK_URL,
            "webhookByEvents": False,
            "webhookBase64": False,
            "events": ["MESSAGES_UPSERT"]
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"✅ Success! Webhook is now pointing internally to: {WEBHOOK_URL}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to update webhook: {str(e)}")

if __name__ == "__main__":
    update_webhook()
