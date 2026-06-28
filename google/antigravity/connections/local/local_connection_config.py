class LocalAgentConfig:
    """Pure-Python configuration holder for the Agent connection."""
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        save_dir: str = None,
        conversation_id: str = None,
        system_instructions: str = None,
        **kwargs
    ):
        self.model = model
        self.save_dir = save_dir
        self.conversation_id = conversation_id
        self.system_instructions = system_instructions
