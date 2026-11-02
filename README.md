# SpiceScript Compiler

## Run

Backend (terminal 1):

    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs
    python -m unittest discover -s tests -t . -v

The first registered user becomes admin (can see everyone's logs).

## Endpoints
| Method | Path | Notes |
|---|---|---|
| POST | /api/auth/register, /api/auth/login | {username, password} -> {token, user} |
| POST | /api/auth/logout, GET /api/auth/me | Bearer token |
| GET  | /api/grammar | EBNF, keyword/operator tables, sample programs (public) |
| POST | /api/lex | {source} -> {ok, tokens, errors} |
| POST | /api/parse | {source} -> {ok, ast, errors} |
| POST | /api/semantic | {source} -> {ok, symbol_table, errors} |
| POST | /api/icg | {source} -> {ok, instructions (three-address code), errors} |
| POST | /api/run | {source} -> {ok, output, errors}  final program output |
| POST | /api/run-all | {source} -> every stage + final output; stops at the first failing stage |
| GET  | /api/logs?all=true | own logs; all=true for admin |

Every stage returns {stage, ok, errors[...]} so the UI can treat them the same way.
Every login and stage run is stored in `action_logs` (user, action, stage, status, input snapshot, time).

## Design
Each engine (`lexer`, `parser`, `semantic`, `icg`, `interpreter`) is its own module with one
public function and never imports another engine. `pipeline.py` is the only place they meet:
it feeds one stage's output to the next and reports when a stage is blocked by an earlier error.

## Run the frontend (terminal 2)
    cd frontend
    npm install
    npm run dev          # open http://localhost:5173

Register an account on the login page (the first account is the admin), pick a sample from
the Grammar panel, and press Run all, or click a single stage to run just that engine.

## How to test it (for the examiner)
1. Start the backend and the frontend (see above) and open http://localhost:5173.
2. Register an account, then sign in. The first account is the admin.
3. Open the **Grammar** panel on the left. It shows the language rules, the keyword and operator tables, and sample programs.
4. Load a sample (or type your own program in the **Program** box) and press **Run all**, or click one stage to run only that engine.

| Sample | What to expect |
|---|---|
| Arithmetic | all five stages pass; output `13` and `30` |
| If / else | all stages pass; output `x is bigger` |
| Loop | all stages pass; output `3`, `2`, `1` |
| Nested blocks | all stages pass; output `1`, `two`, `3` |
| Lexical error | Lexical stage fails and marks the bad character; later stages are skipped |
| Semantic error | Lexical and Syntax pass; Semantic reports 3 errors (undeclared variable, redeclaration, type mismatch) |

Try your own errors too: `mix x 5` (missing `into`) fails at Syntax, and a loop with no `done` fails at Syntax with the line it was opened on.

Each engine is independent. `/api/lex`, `/api/parse`, `/api/semantic`, `/api/icg` and `/api/run` each work on their own, and the **Activity log** page shows every action with the user, stage, result and program. Interactive API docs: http://127.0.0.1:8000/docs

Unit tests (94): `cd backend && python -m unittest discover -s tests -t . -v`

## Security
What the app does to protect accounts and the server:

| Area | Protection |
|---|---|
| Passwords | At least 8 characters with a letter and a number, and a few very common ones are refused. Stored only as salted PBKDF2-SHA256 hashes (600,000 rounds), never as text |
| Sign-in | After 5 wrong passwords a username is paused for 15 minutes (this also applies to usernames that do not exist). Unknown and known usernames take the same time to reject, so they cannot be told apart |
| Sessions | A session ends after 8 hours or when the user signs out. Only a hash of each token is stored, so a leaked database cannot be used to sign in |
| Access | Every compiler endpoint needs a signed-in user. Users see only their own activity log; only an admin can see everyone's |
| Abuse | Each user may make 60 compiler requests per minute. Source code is limited to 50,000 characters |
| Hostile programs | Limits stop programs from exhausting the server: numbers up to 18 characters, text up to 10,000 characters, values up to 1e30, 1,000 lines of output, 10,000 execution steps, blocks nested at most 30 deep, 100 operators per expression, and at most 100 syntax errors reported |
| Web | Strict CORS (only the app's own address), no-store caching, nosniff, no framing, and a locked-down content policy on API replies. All database queries are parameterised, and the page never inserts user text as HTML |

Known limits (fine for a lab, not for the open internet): traffic is not encrypted (no HTTPS), the request counters live in memory and reset when the server restarts, there is no password reset by email, and someone can pause another person's sign-in by guessing wrong passwords on purpose.

## Windows quick start
1. Install Python from python.org (tick "Add python.exe to PATH") and Node.js (LTS) from nodejs.org.
2. In the `backend` folder run `python -m pip install fastapi uvicorn httpx`.
3. Double-click `start-spicescript.bat`. It opens the backend and frontend in two windows and then the app. Keep both windows open.
