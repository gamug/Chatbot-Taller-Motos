import queue, threading

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


# in app.py
answer_done_event = threading.Event()

# pass it to the handler
class AnswerCallbackHandler:
    def __init__(self, text_q: queue.Queue, done_event: threading.Event):
        self.text_q = text_q
        self.done_event = done_event

    def done(self):
        self.done_event.set()  # signal frontend to freeze

    def __call__(self, **kwargs):
        if self.done_event.is_set():
            return
        event = kwargs.get("event", {})
        text = event.get("contentBlockDelta", {}).get("delta", {}).get("text", "")
        if text:
            self.text_q.put(text)