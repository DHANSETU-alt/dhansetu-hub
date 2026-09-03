"""Persistent, governed Angella mission control (records policy; executes nothing)."""
from __future__ import annotations
import hashlib, json, re, sqlite3, uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
from .config import project_root, state_dir
from .event_bus import AgentEvent, EventBus

def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

class MissionState(StrEnum):
    RECEIVED="RECEIVED"; UNDERSTANDING="UNDERSTANDING"; PLANNING="PLANNING"
    WAITING_FOR_APPROVAL="WAITING_FOR_APPROVAL"; ASSIGNED="ASSIGNED"; IN_PROGRESS="IN_PROGRESS"
    MONITORING="MONITORING"; VALIDATING="VALIDATING"; FAILED_ATTEMPT="FAILED_ATTEMPT"
    REPLANNING="REPLANNING"; RETRAINING_AGENT="RETRAINING_AGENT"; RETRYING="RETRYING"
    BLOCKED_EXTERNAL="BLOCKED_EXTERNAL"; COMPLETE="COMPLETE"; CANCELLED="CANCELLED"
    WAITING_FOR_FOUNDER="WAITING_FOR_FOUNDER"; FAILED_WITH_ESCALATION="FAILED_WITH_ESCALATION"

TERMINAL={MissionState.COMPLETE,MissionState.BLOCKED_EXTERNAL,MissionState.CANCELLED,MissionState.WAITING_FOR_FOUNDER,MissionState.FAILED_WITH_ESCALATION}

@dataclass(frozen=True)
class Strategy:
    strategy_id:str; approach:str; likelihood:int; risk:int; cost:int; time:int; reversibility:int; evidence:str
    @property
    def score(self): return self.likelihood+self.reversibility-self.risk-self.cost-self.time

class ExecutiveLoop:
    """SQLite mission owner with approval, follow-up and no-repeat policy."""
    def __init__(self,path:Path|None=None,bus:EventBus|None=None):
        self.path=path or state_dir()/"angella_executive.db"; self.bus=bus or EventBus()
        self.path.parent.mkdir(parents=True,exist_ok=True); self._schema()
    def db(self):
        c=sqlite3.connect(self.path,timeout=10); c.row_factory=sqlite3.Row; return c
    def _schema(self):
        with self.db() as c: c.executescript("""
        CREATE TABLE IF NOT EXISTS missions(id TEXT PRIMARY KEY,command TEXT,prompt TEXT,state TEXT,risk TEXT,approval INTEGER,acceptance TEXT,confidence INTEGER,strategy TEXT,last_followup TEXT,next_followup TEXT,created TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,mission TEXT,title TEXT,owner TEXT,dependencies TEXT,risk TEXT,acceptance TEXT,status TEXT,stage TEXT,created TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,payload TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS heartbeats(id INTEGER PRIMARY KEY,agent TEXT,task TEXT,status TEXT,stage TEXT,blocker TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS followups(id TEXT PRIMARY KEY,mission TEXT,task TEXT,agent TEXT,level INTEGER,due TEXT,status TEXT,response TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS failures(id TEXT PRIMARY KEY,mission TEXT,task TEXT,agent TEXT,strategy TEXT,fingerprint TEXT,payload TEXT,created TEXT);
        CREATE INDEX IF NOT EXISTS failure_lookup ON failures(fingerprint,strategy);
        CREATE TABLE IF NOT EXISTS strategies(id TEXT PRIMARY KEY,fingerprint TEXT,payload TEXT,result TEXT,environment TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS coaching(id TEXT PRIMARY KEY,mission TEXT,task TEXT,agent TEXT,payload TEXT,status TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS lessons(id TEXT PRIMARY KEY,mission TEXT,payload TEXT,validated INTEGER,created TEXT);
        CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,mission TEXT,payload TEXT,created TEXT);
        """)
    def event(self,mission,action,message,target="Angella Executive Loop",task=None,status="RECORDED"):
        self.bus.publish(AgentEvent(mission_id=mission,task_id=task,source_agent="Angella Executive Loop",target_agent=target,action=action,status=status,message=message,repo=str(project_root()),subsystem="angella_executive_loop"))
    @staticmethod
    def engineer(command,acceptance):
        command=" ".join(command.split())
        if not command: raise ValueError("empty Founder command")
        return f"PROJECT:\nSHAKTHI_OS 3.1\n\nOBJECTIVE:\n{command}\n\nCONSTRAINTS:\n- preserve working functionality\n- no fabricated live data\n- governance, least privilege, audit and rollback\n\nTASKS:\n1. inspect\n2. plan\n3. delegate\n4. verify\n5. report and learn\n\nACCEPTANCE:\n"+"\n".join(f"- {x}" for x in acceptance)
    def create(self,command,*,risk="NORMAL",acceptance=None,confidence=60):
        if not 0<=confidence<=100: raise ValueError("bad confidence")
        acceptance=acceptance or ["tests pass","runtime evidence exists","Guardian review recorded"]
        sensitive=(risk.upper() in {"HIGH","CRITICAL"} or any(x in command.lower() for x in ("credential","real payment","settlement","firewall","delete data","authentication")))
        mid,t=uid("MISSION"),now(); state=MissionState.WAITING_FOR_APPROVAL if sensitive else MissionState.PLANNING
        with self.db() as c: c.execute("INSERT INTO missions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(mid,command,self.engineer(command,acceptance),state,risk.upper(),int(sensitive),json.dumps(acceptance),confidence,None,None,None,t,t))
        self.event(mid,"MISSION_CREATED",f"risk={risk.upper()}","Mission Planner"); self.event(mid,"PROMPT_ENGINEERED","Founder command structured","Prompt Architect")
        return self.mission(mid)
    def add_task(self,mid,title,*,dependencies=None,risk="NORMAL",acceptance=None):
        self.mission(mid); tid,t=uid("TASK"),now()
        with self.db() as c: c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?)",(tid,mid,title,None,json.dumps(dependencies or []),risk,json.dumps(acceptance or []),"PLANNED","PLANNING",t,t))
        self.event(mid,"PLAN_CREATED",title,"Mission Planner",tid); return self.task(tid)
    def register(self,agent):
        required={"agent_id","name","capabilities","tools","permissions","supported_task_types"}
        if required-agent.keys(): raise ValueError(f"missing {sorted(required-agent.keys())}")
        payload={"confidence":50,"historical_success_rate":0,"average_completion_time":None,"failure_history":[],"current_load":0,"status":"AVAILABLE","version":"1.0.0","training_level":"BASELINE"}|agent
        with self.db() as c: c.execute("INSERT OR REPLACE INTO agents VALUES(?,?,?)",(payload["agent_id"],json.dumps(payload),now()))
    def select(self,capabilities,permissions=None):
        needed,perms=set(capabilities),set(permissions or [])
        with self.db() as c: agents=[json.loads(r[0]) for r in c.execute("SELECT payload FROM agents")]
        choices=[]
        for a in agents:
            if needed<=set(a["capabilities"]) and perms<=set(a["permissions"]) and a["status"] in {"AVAILABLE","ACTIVE"}:
                score=25*len(needed)+.35*a["historical_success_rate"]+.2*a["confidence"]-10*a["current_load"]-4*len(a["failure_history"]); choices.append((score,a))
        if not choices: raise LookupError("no eligible agent")
        return max(choices,key=lambda x:x[0])[1]
    def assign(self,tid,agent,followup_seconds=300):
        task=self.task(tid); due=(datetime.now(timezone.utc)+timedelta(seconds=followup_seconds)).isoformat(); t=now()
        with self.db() as c:
            if not c.execute("SELECT 1 FROM agents WHERE id=?",(agent,)).fetchone(): raise LookupError(agent)
            c.execute("UPDATE tasks SET owner=?,status='ASSIGNED',updated=? WHERE id=?",(agent,t,tid)); c.execute("INSERT INTO followups VALUES(?,?,?,?,?,?,?,?,?)",(uid("FOLLOWUP"),task["mission"],tid,agent,1,due,"SCHEDULED",None,t)); c.execute("UPDATE missions SET state=?,next_followup=?,updated=? WHERE id=?",(MissionState.ASSIGNED,due,t,task["mission"]))
        self.event(task["mission"],"AGENT_ASSIGNED",f"assigned {agent}",agent,tid); return self.task(tid)
    def heartbeat(self,tid,agent,stage,blocker=None):
        if stage not in {"INSPECTING","PLANNING","IMPLEMENTING","TESTING","BUILDING","VERIFYING"}: raise ValueError("invalid stage")
        task=self.task(tid); t=now(); status="BLOCKED" if blocker else "ACTIVE"
        with self.db() as c: c.execute("INSERT INTO heartbeats(agent,task,status,stage,blocker,created) VALUES(?,?,?,?,?,?)",(agent,tid,status,stage,blocker,t)); c.execute("UPDATE tasks SET status=?,stage=?,updated=? WHERE id=?",("BLOCKED" if blocker else "IN_PROGRESS",stage,t,tid)); c.execute("UPDATE missions SET state=?,updated=? WHERE id=?",(MissionState.MONITORING,t,task["mission"]))
        self.event(task["mission"],"BLOCKER_DETECTED" if blocker else "HEARTBEAT",blocker or stage,"Angella Executive Loop",tid)
    def due_followups(self):
        with self.db() as c: return [dict(r) for r in c.execute("SELECT * FROM followups WHERE status='SCHEDULED' AND due<=?",(now(),))]
    def followup(self,fid,response=None):
        with self.db() as c:
            r=c.execute("SELECT * FROM followups WHERE id=?",(fid,)).fetchone()
            if not r: raise LookupError(fid)
            c.execute("UPDATE followups SET status='COMPLETED',response=? WHERE id=?",(response,fid)); c.execute("UPDATE missions SET last_followup=?,updated=? WHERE id=?",(now(),now(),r["mission"]))
        self.event(r["mission"],"FOLLOW_UP",response or "follow-up requested",r["agent"],r["task"])
    @staticmethod
    def fingerprint(category,problem,root,environment):
        base="|".join(re.sub(r"[^A-Z0-9]+","_",x.upper()).strip("_") for x in (category,problem,root)); context=json.dumps({k:environment[k] for k in sorted(environment) if k in {"framework","version","os","architecture","hardware"}},sort_keys=True)
        return f"{base}:{hashlib.sha256(context.encode()).hexdigest()[:12]}"
    def fail(self,mid,tid,agent,strategy,*,category,problem,root,error,evidence,attempt,why,environment):
        fp=self.fingerprint(category,problem,root,environment); payload={"root_cause":root,"error":error,"evidence":evidence,"attempted_solution":attempt,"why_it_failed":why,"environment":environment,"result":"FAILED"}; t=now()
        with self.db() as c: c.execute("INSERT INTO failures VALUES(?,?,?,?,?,?,?,?)",(uid("FAILURE"),mid,tid,agent,strategy,fp,json.dumps(payload),t)); c.execute("INSERT OR REPLACE INTO strategies VALUES(?,?,?,?,?,?)",(strategy,fp,json.dumps({"approach":attempt}),"FAILED",json.dumps(environment),t)); c.execute("UPDATE missions SET state=?,updated=? WHERE id=?",(MissionState.FAILED_ATTEMPT,t,mid))
        self.event(mid,"STRATEGY_FAILED",f"{fp} {strategy}","Failure Memory",tid,"FAILED"); return fp
    def choose(self,mid,tid,fp,candidates,environment_changed=False,reason=None):
        if len(candidates)<3: raise ValueError("three strategies required")
        with self.db() as c: failed={r[0] for r in c.execute("SELECT id FROM strategies WHERE fingerprint=? AND result='FAILED'",(fp,))}
        allowed=[]
        for s in candidates:
            if s.strategy_id in failed and not(environment_changed and reason): self.event(mid,"STRATEGY_REJECTED_FROM_MEMORY",f"REPEATED FAILED STRATEGY PREVENTED: {s.strategy_id}","Failure Memory",tid)
            else: allowed.append(s)
        if not allowed: raise RuntimeError("all strategies blocked")
        chosen=max(allowed,key=lambda x:x.score)
        with self.db() as c: c.execute("INSERT OR REPLACE INTO strategies VALUES(?,?,?,?,?,?)",(chosen.strategy_id,fp,json.dumps(asdict(chosen)),"SELECTED",json.dumps({"changed":environment_changed,"reason":reason}),now())); c.execute("UPDATE missions SET state=?,strategy=?,updated=? WHERE id=?",(MissionState.REPLANNING,chosen.strategy_id,now(),mid))
        self.event(mid,"NEW_STRATEGY_SELECTED",chosen.approach,"Mission Planner",tid); return chosen
    def coach(self,mid,tid,agent,gap,changes,verification,mistakes):
        payload={"gap":gap,"required_changes":changes,"acceptance_tests":verification,"known_mistakes":mistakes,"instruction_version":"candidate-1","production_prompt_modified":False}; cid=uid("COACH")
        with self.db() as c: c.execute("INSERT INTO coaching VALUES(?,?,?,?,?,?,?)",(cid,mid,tid,agent,json.dumps(payload),"ACTIVE",now())); c.execute("UPDATE missions SET state=?,updated=? WHERE id=?",(MissionState.RETRAINING_AGENT,now(),mid))
        self.event(mid,"AGENT_COACHED",cid,agent,tid); return payload
    def complete_task(self,tid,evidence):
        if not evidence: raise ValueError("evidence required")
        task=self.task(tid)
        with self.db() as c: c.execute("UPDATE tasks SET status='COMPLETE',stage='VERIFYING',updated=? WHERE id=?",(now(),tid))
        self.event(task["mission"],"TEST_PASSED","; ".join(evidence),"Guardian",tid,"SUCCESS")
    def transition(self,mid,state,evidence=None):
        evidence=evidence or []
        if state==MissionState.COMPLETE:
            with self.db() as c: incomplete=c.execute("SELECT count(*) FROM tasks WHERE mission=? AND status!='COMPLETE'",(mid,)).fetchone()[0]
            if incomplete or not evidence: raise ValueError("completion gate failed")
        with self.db() as c: c.execute("UPDATE missions SET state=?,updated=? WHERE id=?",(state,now(),mid))
        action={MissionState.VALIDATING:"MISSION_VALIDATING",MissionState.COMPLETE:"MISSION_COMPLETE",MissionState.BLOCKED_EXTERNAL:"MISSION_BLOCKED",MissionState.WAITING_FOR_FOUNDER:"MISSION_BLOCKED",MissionState.FAILED_WITH_ESCALATION:"MISSION_BLOCKED"}.get(state)
        if action:self.event(mid,action,"; ".join(evidence) or state,"Founder" if state!=MissionState.VALIDATING else "Guardian",status="SUCCESS" if state==MissionState.COMPLETE else "RECORDED")
        return self.mission(mid)
    def mission(self,mid):
        with self.db() as c:r=c.execute("SELECT * FROM missions WHERE id=?",(mid,)).fetchone()
        if not r:raise LookupError(mid)
        d=dict(r);d["acceptance"]=json.loads(d["acceptance"]);d["approval"]=bool(d["approval"]);return d
    def task(self,tid):
        with self.db() as c:r=c.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
        if not r:raise LookupError(tid)
        d=dict(r);d["dependencies"]=json.loads(d["dependencies"]);d["acceptance"]=json.loads(d["acceptance"]);return d
    def snapshot(self):
        with self.db() as c:
            ms=[dict(r) for r in c.execute("SELECT * FROM missions ORDER BY updated DESC LIMIT 20")];ts=[dict(r) for r in c.execute("SELECT * FROM tasks ORDER BY updated DESC LIMIT 50")];fs=[dict(r) for r in c.execute("SELECT id,mission,task,agent,strategy,fingerprint,created FROM failures ORDER BY created DESC LIMIT 20")];cs=[dict(r) for r in c.execute("SELECT id,mission,task,agent,status,created FROM coaching ORDER BY created DESC LIMIT 20")];fu=[dict(r) for r in c.execute("SELECT * FROM followups WHERE status='SCHEDULED' ORDER BY due LIMIT 20")]
        active=[m for m in ms if MissionState(m["state"]) not in TERMINAL]
        return {"source":"LIVE SQLITE CONTROL PLANE","generated_at":now(),"angella_status":"ACTIVE" if active else "IDLE","missions":ms,"tasks":ts,"failures":fs,"coaching":cs,"followups":fu,"counts":{"active_missions":len(active),"open_tasks":sum(t["status"]!="COMPLETE" for t in ts),"failures":len(fs),"training":sum(x["status"]=="ACTIVE" for x in cs)}}
