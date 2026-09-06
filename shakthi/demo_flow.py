"""Safe local visual demo using the real SHAKTHI event bus."""
from __future__ import annotations
import threading, time, uuid
from pathlib import Path
from .event_bus import AgentEvent, EventBus

class DemoFlow:
    def __init__(self,bus:EventBus|None=None): self.bus=bus or EventBus(); self.stop_event=threading.Event(); self.thread=None; self.mission=None
    def state(self): return {"source":"LOCAL TEST / DEMO EVENT SOURCE","running":bool(self.thread and self.thread.is_alive()),"mission_id":self.mission,"label":"SHAKTHI_OS LIVE DEMO — LOCAL / TEST"}
    def publish(self,source,target,action,status,message):
        self.bus.publish(AgentEvent(mission_id=self.mission,source_agent=source,target_agent=target,action=action,status=status,message=f"DEMO EVENT SOURCE — {message}",repo=str(Path(__file__).resolve().parents[1]),subsystem="local_visual_demo",data_source="LOCAL TEST / DEMO EVENT SOURCE"))
    def start(self):
        if self.thread and self.thread.is_alive(): return self.state()
        self.stop_event.clear(); self.mission=f"DEMO-{uuid.uuid4().hex[:8].upper()}"; self.thread=threading.Thread(target=self.run,name="shakthi-local-demo",daemon=True); self.thread.start(); return self.state()
    def stop(self): self.stop_event.set(); return self.state()
    def wait(self,seconds): return self.stop_event.wait(seconds)
    def run(self):
        normal=[("Founder","Angela Executive Command Center","MISSION_CREATED","RUNNING","Safe demo mission received"),("Angela Executive Command Center","SHAKTHI Prompt Architect","PROMPT_ENGINEERED","RUNNING","Prompt engineered"),("SHAKTHI Prompt Architect","Codex Engineering Agent","AGENT_ASSIGNED","RUNNING","Local test task assigned"),("Codex Engineering Agent","QA Agent","TEST_PASSED","SUCCESS","Controlled test passed"),("QA Agent","SHAKTHI Guardian","MISSION_VALIDATING","RUNNING","QA evidence sent to Guardian"),("SHAKTHI Guardian","Angela Executive Command Center","GUARDIAN_APPROVED","SUCCESS","Local demo approved"),("Angela Executive Command Center","Founder","MISSION_COMPLETE","SUCCESS","Normal workflow returned to Founder")]
        blocked=[("Angela Executive Command Center","Codex Engineering Agent","AGENT_ASSIGNED","RUNNING","Blocked-case task assigned"),("Codex Engineering Agent","Angela Executive Command Center","BLOCKER_DETECTED","BLOCKED","Harmless local test blocker"),("Angela Executive Command Center","Codex Engineering Agent","RETRY_STARTED","RUNNING","Test blocker resolved")]
        recovery=[("Codex Engineering Agent","SHAKTHI Guardian","TEST_FAILED","FAILED","Controlled local assertion failure"),("SHAKTHI Guardian","Bug Fixer Agent","BLOCKER_DETECTED","BLOCKED","Recovery review requested"),("Bug Fixer Agent","QA Agent","NEW_STRATEGY_SELECTED","RUNNING","Alternative safe strategy applied"),("QA Agent","SHAKTHI Guardian","TEST_PASSED","SUCCESS","Recovery test passed"),("SHAKTHI Guardian","Angela Executive Command Center","GUARDIAN_APPROVED","SUCCESS","Recovery verified"),("Angela Executive Command Center","Founder","MISSION_COMPLETE","SUCCESS","Recovery flow complete")]
        while not self.stop_event.is_set():
            for sequence in (normal,blocked,recovery):
                for event in sequence:
                    if self.stop_event.is_set(): return
                    self.publish(*event)
                    if self.wait(2.4): return
                if self.wait(3): return
