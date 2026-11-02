"""
SpiceScript compiler backend.

Each compiler stage is its own endpoint and runs independently.
Every login and stage run is written to action_logs.
"""
import math
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from . import db
from .grammar import GRAMMAR_EBNF, KEYWORD_TABLE, OPERATOR_TABLE, SAMPLES
from . import pipeline
from .lexer import lex


@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    yield


app = FastAPI(title="SpiceScript Compiler", lifespan=lifespan)

# Only the app's own addresses may call the API from a browser. (The dev server also
# forwards /api itself, so normal use never needs CORS at all.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"   # never keep answers (or tokens) in a cache
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


# ---- models -----------------------------------------------------------------

USERNAME = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
COMMON_PASSWORDS = {"password1", "password123", "qwerty123", "abc12345", "iloveyou1", "welcome1", "admin123"}


class LoginIn(BaseModel):
    username: str = USERNAME
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    username: str = USERNAME
    password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one number")
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("That password is too common; choose another")
        return v


class SourceIn(BaseModel):
    source: str = Field(max_length=50_000)


# ---- auth helpers -----------------------------------------------------------

def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get_user_by_token(authorization.split(" ", 1)[1].strip())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def public_user(user) -> dict:
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


# Each user may run the compiler this many times per window; stops one client hogging the server.
RATE_LIMIT = 60
RATE_WINDOW = 60
_recent_calls = defaultdict(deque)


def limited_user(user=Depends(current_user)):
    calls, now = _recent_calls[user["id"]], time.monotonic()
    while calls and now - calls[0] > RATE_WINDOW:
        calls.popleft()
    if len(calls) >= RATE_LIMIT:
        wait = math.ceil(RATE_WINDOW - (now - calls[0]))
        raise HTTPException(status_code=429, detail=f"Too many requests. Try again in {wait} seconds.",
                            headers={"Retry-After": str(wait)})
    calls.append(now)
    return user


# ---- auth routes ------------------------------------------------------------

@app.post("/api/auth/register")
def register(creds: RegisterIn):
    user = db.create_user(creds.username, creds.password)
    if not user:
        raise HTTPException(status_code=409, detail="Username already taken")
    db.add_log(user["id"], user["username"], "register", status="success")
    token = db.create_session(user["id"])
    return {"token": token, "user": public_user(user)}


def locked_out(wait: int) -> HTTPException:
    minutes = math.ceil(wait / 60)
    return HTTPException(status_code=429, headers={"Retry-After": str(wait)},
                         detail=f"Too many failed sign-in attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.")


@app.post("/api/auth/login")
def login(creds: LoginIn):
    wait = db.lockout_seconds(creds.username)
    if wait:
        raise locked_out(wait)

    user = db.get_user_by_name(creds.username)
    if user:
        valid = db.verify_password(creds.password, user["salt"], user["password_hash"])
    else:
        db.burn_time(creds.password)   # same delay whether or not the username exists
        valid = False

    if not valid:
        db.record_login_failure(creds.username)
        wait = db.lockout_seconds(creds.username)
        db.add_log(user["id"] if user else None, creds.username, "login", status="error",
                   detail="Invalid credentials" + (f" - locked for {db.LOCKOUT_SECONDS // 60} minutes" if wait else ""))
        if wait:
            raise locked_out(wait)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    db.clear_login_failures(creds.username)
    db.purge_expired_sessions()
    db.add_log(user["id"], user["username"], "login", status="success")
    return {"token": db.create_session(user["id"]), "user": public_user(user)}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None), user=Depends(current_user)):
    db.delete_session(authorization.split(" ", 1)[1].strip())
    db.add_log(user["id"], user["username"], "logout", status="success")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return public_user(user)


# ---- public info (grammar panel) -------------------------------------------

@app.get("/api/grammar")
def grammar():
    return {
        "language": "SpiceScript",
        "ebnf": GRAMMAR_EBNF,
        "keywords": KEYWORD_TABLE,
        "operators": OPERATOR_TABLE,
        "samples": SAMPLES,
    }


# ---- compiler stages --------------------------------------------------------
# Each endpoint runs its stage on its own (earlier stages are run only to feed it) and
# every result has the same {stage, ok, errors, ...} shape.

def run_stage(stage: str, user, source: str, runner) -> dict:
    try:
        result = runner(source)
    except (RecursionError, MemoryError, OverflowError):   # a program too big or too tangled to process
        result = {"stage": stage, "ok": False,
                  "errors": [{"stage": stage, "line": 1, "col": 1,
                              "message": "This program is too large or complex to process"}]}
    status = "success" if result.get("ok") else "error"
    detail = None
    if status == "error":
        detail = f'{len(result.get("errors", []))} error(s)'
        if result.get("stopped_at"):
            detail = f'stopped at {result["stopped_at"]}: {detail}'
        elif result.get("blocked_by"):
            detail = f'blocked by {result["blocked_by"]}: {detail}'
    db.add_log(user["id"], user["username"], "run_stage", stage=stage, status=status,
               input_snapshot=source, detail=detail)
    return result


@app.post("/api/lex")
def api_lex(body: SourceIn, user=Depends(limited_user)):
    return run_stage("lexical", user, body.source, lex)


@app.post("/api/parse")
def api_parse(body: SourceIn, user=Depends(limited_user)):
    return run_stage("syntax", user, body.source, lambda src: pipeline.run_single(src, "syntax"))


@app.post("/api/semantic")
def api_semantic(body: SourceIn, user=Depends(limited_user)):
    return run_stage("semantic", user, body.source, lambda src: pipeline.run_single(src, "semantic"))


@app.post("/api/icg")
def api_icg(body: SourceIn, user=Depends(limited_user)):
    return run_stage("icg", user, body.source, lambda src: pipeline.run_single(src, "icg"))


@app.post("/api/run")
def api_run(body: SourceIn, user=Depends(limited_user)):
    """Final output of the program (runs every earlier stage first)."""
    return run_stage("run", user, body.source, lambda src: pipeline.run_single(src, "run"))


@app.post("/api/run-all")
def api_run_all(body: SourceIn, user=Depends(limited_user)):
    """The complete compilation process in one call, logged as a single 'full' action."""
    return run_stage("full", user, body.source, pipeline.run_all)


# ---- logs -------------------------------------------------------------------

@app.get("/api/logs")
def logs(all: bool = False, limit: int = 200, user=Depends(current_user)):
    limit = max(1, min(limit, 1000))
    if all:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admins only")
        return db.get_logs(None, limit)
    return db.get_logs(user["id"], limit)
