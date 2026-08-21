import os 
from dotenv import load_dotenv
from google import genai


load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINIAI_API_KEY"))

chat = client.chats.create(
    model="gemini-3.7-flash",
    config = {
        "system_instruction": "You are a helpful assistant that provides concise , clear and accurate answers to user queries."
    }
)

print("Ai agent is ready , type 'q' to exit")
while True: 
    user_input = input("\nYou: ")
    if user_input.lower() == 'q':
        print("Goodbye!")
        break
    response = chat.send_message(user_input)
    print(f"AGENT RESPONSE: {response.text}")
