{
    open Parser
    exception Error of string
}

let digit = ['0'-'9']
let letter = ['a'-'z' 'A'-'Z' '_'] 
let id = letter (letter | digit)*
let whitespace = [' ' '\t' '\r' '\n']+
let int = digit+

rule read = parse
    | whitespace { read lexbuf }
    | "(*" { comment lexbuf }

    (* Section delimiters - MUST come before ID *)
    | "regulation" { REGULATION }
    | "version" { VERSION }
    | "effective_date" | "effective date" { EFFECTIVE_DATE }
    | "type declaration start" | "type declaration starts" | "type_declaration_start" | "type_declaration_starts" { TYPE_DECL_START }
    | "type declaration end" | "type declaration ends" | "type_declaration_end" | "type_declaration_ends" { TYPE_DECL_ENDS }
    | "policy start" | "policy starts" | "policy_start" | "policy_starts" { POLICY_START }
    | "policy end" | "policy ends" | "policy_end" | "policy_ends" { POLICY_END }
    | "type" { TYPE }

    (* Boolean constants - MUST come before ID *)
    | "True" | "true" | "TRUE" | "⊤" { TRUE } 
    | "False" | "false" | "FALSE" | "⊥" { FALSE }
    
    (* Quantifiers - MUST come before ID *)
    | "Forall" | "forall" | "∀" { FORALL }
    | '\226' '\136' '\128' { FORALL }
    | "Exists" | "exists" | "∃" { EXISTS }
    | '\226' '\136' '\131' { EXISTS }

    (* Propositional operators - MUST come before ID *)
    | "Not" | "not" { NOT }
    | "And" | "and" { AND }
    | "Or" | "or" { OR }
    | "Implies" | "implies" { IMPLIES }
    | "Iff" | "iff" { IFF }
    | "Xor" | "xor" { XOR }

    (* Temporal operators - MUST come before ID *)
    | "Globally" | "globally" | "Always" | "always" | "G" { ALWAYS }
    | "Finally" | "finally" | "Eventually" | "eventually" | "F" { EVENTUALLY }
    | "Next" | "next" | "X" { NEXT }
    | "Until" | "until" | "U" { UNTIL }
    | "Historically" | "historically" | "H" { HISTORICALLY }
    | "Yesterday" | "yesterday" | "Previously" | "previously" | "Y" { YESTERDAY }
    | "Once" | "once" | "O" { ONCE }
    | "Since" | "since" | "S" { SINCE }

    (* Citation *)
    | "@[" { AT_LBRACKET }
    | '"' { read_string (Buffer.create 17) lexbuf }

    (* Operators - order matters! *)
    | "!" | "¬" | "~" { NOT }
    | '\194' '\172' { NOT }
    | "&&" | "&" | "∧" | "/\\" { AND }
    | '\226' '\136' '\167' { AND }
    | "||" | "|" | "∨" | "\\/" { OR }
    | '\226' '\136' '\168' { OR }
    | "=>" | "→" | "⇒" | "==>" | "-->" | "->" { IMPLIES }
    | '\226' '\134' '\146' { IMPLIES }
    | '\226' '\135' '\146' { IMPLIES }
    | "↔" | "<=>" | "<==>" | "<-->" | "<->" { IFF }
    | '\226' '\134' '\148' { IFF }
    | '\226' '\135' '\148' { IFF }
    | "⊕" { XOR }
    | '\226' '\138' '\149' { XOR }

    (* Comparison operators - order matters! *)
    | "!=" | "≠" { NOTEQUALS }
    | "<=" | "≤" { LESSEQ }
    | ">=" | "≥" { GREATEREQ }
    | "<" { LESS }
    | ">" { GREATER }
    | "=" { EQUALS }

    (* Constants with @ prefix *)
    | '@' (letter (letter | digit)*) as const
      { CONST(String.sub const 1 (String.length const - 1)) }

    (* Integers *)
    | int as i { INT (int_of_string i) }
    
    (* Punctuation *)
    | "(" { LPAREN }
    | ")" { RPAREN }
    | "[" { LBRACKET }
    | "]" { RBRACKET }
    | "," { COMMA }
    | ";" { SEMICOLON }
    | "." { DOT }

    (* Identifiers - MUST come LAST *)
    | id as s { ID s } 
    
    | eof { EOF }
    | _ as c { raise (Error (Printf.sprintf "Unexpected character: %c (code: %d)" c (Char.code c))) }

and comment = parse
    | "*)" { read lexbuf }
    | "(*" { comment lexbuf }
    | eof { raise (Error "Unterminated comment") }
    | _ { comment lexbuf }

and read_string buf = parse
    | '"' { STRING (Buffer.contents buf) }
    | '\\' '"' { Buffer.add_char buf '"'; read_string buf lexbuf }
    | '\\' '\\' { Buffer.add_char buf '\\'; read_string buf lexbuf }
    | '\\' 'n' { Buffer.add_char buf '\n'; read_string buf lexbuf }
    | '\\' 't' { Buffer.add_char buf '\t'; read_string buf lexbuf }
    | [^ '"' '\\']+ as s { Buffer.add_string buf s; read_string buf lexbuf }
    | eof { raise (Error "Unterminated string") }
    | _ as c { Buffer.add_char buf c; read_string buf lexbuf }