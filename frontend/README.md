# SpiceScript frontend

React + Vite. Talks to the FastAPI backend at http://127.0.0.1:8000 (change with `VITE_API_URL`).

    cd frontend
    npm install
    npm run dev        # http://localhost:5173

Start the backend first (see the top-level README). The first account you register becomes the admin.

## Structure
    src/api.js            every backend call, token handling, error messages
    src/stages.js         the five stages and the default program
    src/App.jsx           session handling and page switching
    src/components/
      LoginPage, TopBar
      Workspace           state for the workbench (code, results, which stage is open)
      StageBar            the five stage buttons with status badges, plus Run all
      CodeEditor          line numbers, error markers, auto-indent, Ctrl+Enter
      GrammarPanel        EBNF, keyword and operator tables, sample programs
      StagePanel          header, errors and the view for the open stage
      TokenTable, ParseTree, SymbolTable, TacView, OutputView, ErrorList
      LogsPage            activity log (admins can switch to everyone)
