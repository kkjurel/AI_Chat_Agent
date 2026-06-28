import asyncio
import os
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig

# Load env variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    os.environ["GEMINI_API_KEY"] = api_key

async def main():
    print("Initializing Google Antigravity Agent...")
    
    # 1. Initialize configuration
    # You can specify custom tools, safety policies, or model parameters here.
    config = LocalAgentConfig(
        model="gemini-flash-lite-latest"
        # tools=[my_custom_tool], # Uncomment to add custom python callables as tools
    )
    
    # 2. Run the agent in an asynchronous session
    async with Agent(config) as agent:
        print("Agent ready. Sending prompt...")
        response = await agent.chat("Introduce yourself and list your current capabilities.")
        
        # 3. Print the agent's response
        print("\nAgent Response:")
        print(await response.text())

if __name__ == "__main__":
    asyncio.run(main())
