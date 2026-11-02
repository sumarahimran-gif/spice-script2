"""SpiceScript grammar (EBNF) and sample programs shown in the UI."""

GRAMMAR_EBNF = """\
program     = { statement } "plate" ;

statement   = declaration | assignment | print | if_stmt | while_stmt ;

declaration = "mix" IDENT "into" expr ;
assignment  = IDENT "into" expr ;
print       = "serve" expr ;
if_stmt     = "taste" condition { statement } [ "bland" { statement } ] "done" ;
while_stmt  = "simmer" condition { statement } "done" ;

condition   = expr ;
expr        = additive [ ( "hotter" | "cooler" | "matches" ) additive ] ;
additive    = term { ( "plus" | "peel" ) term } ;
term        = factor { ( "blend" | "slice" ) factor } ;
factor      = NUMBER | STRING | IDENT ;

(* Lexical rules *)
IDENT   = letter { letter | digit | "_" } ;
NUMBER  = digit { digit } [ "." digit { digit } ] ;
STRING  = '"' { any character except '"' and newline } '"' ;
COMMENT = "#" { any character except newline } ;
"""

KEYWORD_TABLE = [
    {"word": "mix", "meaning": "Variable declaration"},
    {"word": "serve", "meaning": "Print / output"},
    {"word": "taste", "meaning": "If condition"},
    {"word": "bland", "meaning": "Else branch"},
    {"word": "simmer", "meaning": "While loop"},
    {"word": "done", "meaning": "Ends a taste/bland or simmer block"},
    {"word": "plate", "meaning": "End of program"},
]

OPERATOR_TABLE = [
    {"word": "into", "symbol": "=", "meaning": "Assignment"},
    {"word": "plus", "symbol": "+", "meaning": "Addition"},
    {"word": "peel", "symbol": "-", "meaning": "Subtraction"},
    {"word": "blend", "symbol": "*", "meaning": "Multiplication"},
    {"word": "slice", "symbol": "/", "meaning": "Division"},
    {"word": "hotter", "symbol": ">", "meaning": "Greater than"},
    {"word": "cooler", "symbol": "<", "meaning": "Less than"},
    {"word": "matches", "symbol": "==", "meaning": "Equal to"},
]

SAMPLES = [
    {
        "name": "Arithmetic",
        "code": """\
mix x into 10
mix y into 3
mix sum into x plus y
mix product into x blend y
serve sum
serve product
plate
""",
    },
    {
        "name": "If / else",
        "code": """\
mix x into 10
mix y into 3
taste x hotter y
  serve "x is bigger"
bland
  serve "y is bigger or equal"
done
plate
""",
    },
    {
        "name": "Loop",
        "code": """\
mix x into 3
simmer x hotter 0
  serve x
  x into x peel 1
done
plate
""",
    },
    {
        "name": "Nested blocks",
        "code": """\
mix i into 1
simmer i cooler 4
  taste i matches 2
    serve "two"
  bland
    serve i
  done
  i into i plus 1
done
plate
""",
    },
    {
        "name": "Lexical error",
        "code": """\
mix x into 10 @
serve "oops
mix 9lives into 1
plate
""",
    },
    {
        "name": "Semantic error",
        "code": """\
serve z
mix a into 1
mix a into 2
mix s into "hi" plus 5
plate
""",
    },
]
