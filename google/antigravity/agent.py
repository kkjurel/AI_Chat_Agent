import os
import json
import uuid
import asyncio
from typing import Any
from google import genai
from google.genai import types as genai_types

class MockChatResponse:
    def __init__(self, text: str):
        self._text = text

    async def text(self) -> str:
        return self._text

class Agent:
    """Pure-Python Agent class that interacts with Gemini API directly."""
    def __init__(self, config: Any):
        self._config = config
        self.conversation_id = config.conversation_id or uuid.uuid4().hex
        self._history = []
        self._client = None
        self._chat = None

    async def __aenter__(self) -> "Agent":
        api_key = os.getenv("GEMINI_API_KEY")
        self._client = genai.Client(api_key=api_key)
        
        # Load history if it exists
        if self._config.save_dir:
            os.makedirs(self._config.save_dir, exist_ok=True)
            history_file = os.path.join(self._config.save_dir, f"conversation_{self.conversation_id}.json")
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        self._history = json.load(f)
                except Exception:
                    self._history = []

        # Convert simple history dicts to GenAI Content types
        genai_history = []
        for turn in self._history:
            role = turn.get("role")
            parts = turn.get("parts", [])
            # Normalize roles for Gemini API (must be 'user' or 'model')
            if role == "model":
                role_val = "model"
            else:
                role_val = "user"
            
            genai_history.append(
                genai_types.Content(
                    role=role_val,
                    parts=[genai_types.Part.from_text(text=p) for p in parts if isinstance(p, str)]
                )
            )

        # Select model (default to gemini-2.5-flash)
        model_name = self._config.model or "gemini-2.5-flash"
        # Map older or placeholder model names
        if "gemini-flash-lite" in model_name:
            model_name = "gemini-2.5-flash"

        # System instructions
        system_instruction = self._config.system_instructions
        if hasattr(system_instruction, "system_instruction"):
            system_instruction = system_instruction.system_instruction

        chat_config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        )

        self._chat = self._client.chats.create(
            model=model_name,
            history=genai_history,
            config=chat_config
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Save history back to file on exit
        if self._config.save_dir and self._chat:
            history_file = os.path.join(self._config.save_dir, f"conversation_{self.conversation_id}.json")
            history_list = []
            try:
                for message in self._chat.get_history():
                    role = message.role
                    parts = [p.text for p in message.parts if p.text]
                    history_list.append({
                        "role": role,
                        "parts": parts
                    })
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_list, f, indent=4, ensure_ascii=False)
            except Exception:
                pass

    async def chat(self, prompt: str) -> MockChatResponse:
        # Run in executor to prevent blocking async telethon loop since genai SDK is sync
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._chat.send_message(prompt)
        )
        return MockChatResponse(response.text)
