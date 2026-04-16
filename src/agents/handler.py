import queue
import threading

class OrchestratorCallbackHandler:
    def __init__(self, q: queue.Queue, download_q: queue.Queue):
        self.q = q
        self.download_q = download_q
        self.current_tool = None
        self.tool_executing = False

    def __call__(self, **kwargs):
        event = kwargs.get("event", {})

        tool_use = event.get("contentBlockStart", {}).get("start", {}).get("toolUse", {})
        if tool_use:
            self.current_tool = tool_use.get("name", "tool")
            self.tool_executing = True
            self.q.put(f"⚙️ Ejecutando: `{self.current_tool}`...")
            return

        if "messageStart" in event and self.tool_executing:
            self.tool_executing = False
            self.q.put(f"✅ `{self.current_tool}` completado")
            self.current_tool = None
            return


class AnswerCallbackHandler:
    """
    Handler for streaming text from answer agent.
    Queues are set at runtime, not at import time.
    """
    def __init__(self, q: queue.Queue, text_q: queue.Queue, download_q: queue.Queue):
        self.q = q
        self.text_q = text_q
        self.download_q = download_q
        self.current_tool = None
        self.tool_executing = False

    def __call__(self, **kwargs):
        event = kwargs.get("event", {})

        text = event.get("contentBlockDelta", {}).get("delta", {}).get("text", "")
        if text:
            self.text_q.put(text)
            return

        tool_use = event.get("contentBlockStart", {}).get("start", {}).get("toolUse", {})
        if tool_use:
            self.current_tool = tool_use.get("name", "tool")
            self.tool_executing = True
            self.q.put(f"⚙️ Ejecutando: `{self.current_tool}`...")
            return

        if "messageStart" in event and self.tool_executing:
            self.tool_executing = False
            self.q.put(f"✅ `{self.current_tool}` completado")
            self.current_tool = None
            return
        
        
class StreamlitCallbackHandler:
    def __init__(self, q: queue.Queue, text_q: queue.Queue, download_q: queue.Queue):
        self.q = q
        self.text_q = text_q
        self.download_q = download_q
        self.current_tool = None
        self.tool_executing = False

    def __call__(self, **kwargs):
        event = kwargs.get("event", {})

        text = event.get("contentBlockDelta", {}).get("delta", {}).get("text", "")
        if text:
            self.text_q.put(text)
            return

        tool_use = event.get("contentBlockStart", {}).get("start", {}).get("toolUse", {})
        if tool_use:
            self.current_tool = tool_use.get("name", "tool")
            self.tool_executing = True
            self.q.put(f"⚙️ Ejecutando: `{self.current_tool}`...")
            return

        if "messageStart" in event and self.tool_executing:
            self.tool_executing = False
            self.q.put(f"✅ `{self.current_tool}` completado")
            self.current_tool = None
            return