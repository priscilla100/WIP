/* parser.mly - Fixed Parser Definition */

%{ 
    open Ast
%}

%token <int> INT
%token <string> CONST
%token <string> ID
%token <string> STRING

%token NOT AND OR IFF IMPLIES XOR
%token ALWAYS EVENTUALLY NEXT UNTIL HISTORICALLY ONCE SINCE YESTERDAY
%token TRUE FALSE
%token FORALL EXISTS
%token LPAREN RPAREN LBRACKET RBRACKET COMMA DOT SEMICOLON
%token EQUALS NOTEQUALS LESS LESSEQ GREATER GREATEREQ
%token AT_LBRACKET
%token REGULATION VERSION EFFECTIVE_DATE
%token TYPE_DECL_START TYPE_DECL_ENDS TYPE
%token POLICY_START POLICY_END
%token EOF

/* Precedence Declarations (Lowest to Highest) */
%right IFF
%right IMPLIES
%right UNTIL SINCE
%left OR XOR
%left AND
%left EQUALS NOTEQUALS LESS LESSEQ GREATER GREATEREQ
%nonassoc NOT
%nonassoc NEXT EVENTUALLY ALWAYS YESTERDAY ONCE HISTORICALLY

%start <Ast.ast> main

%%

main:
    | metadata = regulation_metadata?;
      type_section = type_declaration_section?; 
      policy_section = policy_section; 
      EOF 
      { { metadata = metadata;
          type_decls = (match type_section with None -> [] | Some t -> t);
          policies = policy_section } }

regulation_metadata:
    | REGULATION; name = ID; 
      ver = version_clause?;
      date = effective_date_clause?
      { { name = name; version = ver; effective_date = date } }

version_clause:
    | VERSION; v = STRING { v }

effective_date_clause:
    | EFFECTIVE_DATE; d = STRING { d }

type_declaration_section:
    | TYPE_DECL_START; 
      types = type_list; 
      TYPE_DECL_ENDS 
      { types }

type_list:
    | { [] }
    | TYPE; name = ID; rest = type_list { name :: rest }

policy_section:
    | POLICY_START; 
      formulas = list(terminated(annotated_formula, SEMICOLON)); 
      POLICY_END 
      { formulas }

annotated_formula:
    | AT_LBRACKET; cite = STRING; RBRACKET; f = formula
        { Annotated(f, cite) }
    | f = formula
        { f }

formula:
    | simple_formula { $1 }
    | f1 = formula; AND; f2 = formula { BinLogicalOp(And, f1, f2) } 
    | f1 = formula; OR; f2 = formula { BinLogicalOp(Or, f1, f2) }
    | f1 = formula; IFF; f2 = formula { BinLogicalOp(Iff, f1, f2) }
    | f1 = formula; IMPLIES; f2 = formula { BinLogicalOp(Implies, f1, f2) }  
    | f1 = formula; XOR; f2 = formula { BinLogicalOp(Xor, f1, f2) }
    | f1 = formula; UNTIL; b = timebound?; f2 = formula { BinTemporalOp(Until, f1, f2, b) }
    | f1 = formula; SINCE; b = timebound?; f2 = formula { BinTemporalOp(Since, f1, f2, b) }

simple_formula:
    | TRUE { True }
    | FALSE { False }
    | NOT; f = simple_formula { Not f }
    | ALWAYS; b = timebound?; f = simple_formula { UnTemporalOp(Always, f, b) }
    | EVENTUALLY; b = timebound?; f = simple_formula { UnTemporalOp(Eventually, f, b) }
    | NEXT; b = timebound?; f = simple_formula { UnTemporalOp(Next, f, b) }  
    | HISTORICALLY; b = timebound?; f = simple_formula { UnTemporalOp(Historically, f, b) }
    | ONCE; b = timebound?; f = simple_formula { UnTemporalOp(Once, f, b) }
    | YESTERDAY; b = timebound?; f = simple_formula { UnTemporalOp(Yesterday, f, b) }  
    | LPAREN; f = formula; RPAREN { f }
    | FORALL; vars = separated_nonempty_list(COMMA, ID); DOT; f = formula 
        { Quantified(Forall vars, f) }
    | EXISTS; vars = separated_nonempty_list(COMMA, ID); DOT; f = formula 
        { Quantified(Exists vars, f) }
    | t1 = term; EQUALS; t2 = term
        { Predicate("=", [t1; t2]) }
    | t1 = term; NOTEQUALS; t2 = term
        { Predicate("!=", [t1; t2]) }
    | t1 = term; LESS; t2 = term
        { Predicate("<", [t1; t2]) }
    | t1 = term; LESSEQ; t2 = term
        { Predicate("<=", [t1; t2]) }
    | t1 = term; GREATER; t2 = term
        { Predicate(">", [t1; t2]) }
    | t1 = term; GREATEREQ; t2 = term
        { Predicate(">=", [t1; t2]) }
    | a = atomic_formula { a }

atomic_formula:
    | name = ID; LPAREN; args = separated_list(COMMA, term); RPAREN 
        { Predicate(name, args) }
    | name = ID 
        { Predicate(name, []) }
        
term:
    | x = ID { Var x }
    | c = CONST { Const c }
    | n = INT { Const (string_of_int n) }        
    | s = STRING { Const s }                      
    | x = ID; LPAREN; args = separated_list(COMMA, term); RPAREN 
        { Func(x, args) }
timebound:
    | LBRACKET; t1 = INT; COMMA; t2 = INT; RBRACKET { (t1, t2) }
