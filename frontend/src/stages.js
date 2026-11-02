// The five steps of the pipeline, in order. `endpoint` is the backend route for each one.
export const STAGES = [
  {
    id: "lexical",
    label: "Lexical",
    endpoint: "/api/lex",
    blurb: "Splits the code into tokens and reports characters it does not recognise.",
  },
  {
    id: "syntax",
    label: "Syntax",
    endpoint: "/api/parse",
    blurb: "Checks the tokens against the grammar and builds the parse tree.",
  },
  {
    id: "semantic",
    label: "Semantic",
    endpoint: "/api/semantic",
    blurb: "Checks meaning: declared variables, matching types, safe operations.",
  },
  {
    id: "icg",
    label: "Intermediate code",
    endpoint: "/api/icg",
    blurb: "Turns the tree into three-address code with labels for jumps.",
  },
  {
    id: "run",
    label: "Output",
    endpoint: "/api/run",
    blurb: "Runs the intermediate code and shows what the program serves.",
  },
];

export const RUN_ALL_ENDPOINT = "/api/run-all";

export const DEFAULT_SOURCE = `mix x into 3
simmer x hotter 0
  serve x
  x into x peel 1
done
plate
`;
