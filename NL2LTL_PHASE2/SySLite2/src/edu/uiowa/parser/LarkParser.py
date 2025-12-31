'''
Copyright (c) 2020, Board of Trustees of the University of Iowa.
All rights reserved.

Use of this source code is governed by a BSD 3-Clause License that
can be found in the LICENSE file.
'''

from lark import Lark, Transformer, ParseError
from edu.uiowa.parser.Formula import PLTLFormula
import logging

#PLTL Formula Grammar
fml_grammar = r"""
        ?start: formula
        
        ?formula: _binary_expression
                |_unary_expression
                | constant
                | variable
        !constant: "Top"
                | "Bottom"
        _binary_expression: binary_op "(" formula "," formula ")"
        _unary_expression: unary_op ["("] formula [")"]

        !binary_op: "&" | "|" |"S" | "U" | "=>"
        !unary_op: "G"| "H" | "O" | "F" | "!" | "Y" | "X" 
        
        variable: CNAME

        CNAME: ("-"|"_"|LETTER) ("-"|"_"|LETTER|DIGIT)*

        %import common.LETTER
        %import common.DIGIT
        
        %import common.SIGNED_NUMBER
        %import common.WS
        %ignore WS 
"""

#ADT Grammar    
adt_grammar = r"""
        ?start: "(define-fun" func ")"
         
        ?func: _ID "() Formula" formula 
         
        ?formula: "(" "Op2" _binary_expression ")"
                | "(" "Op1" _unary_expression ")"
                | "(" "P" variable ")" 
                | constants
        
        _unary_expression: unary_op formula 

        _binary_expression: binary_op formula formula 
        
        !binary_op: "AND" | "OR" |"IMPLIES" | "S"
        !unary_op: "NOT" | "Y" | "H" | "O"
        
        !variable: NUMBER
        !constants: "Top" | "Bottom"
        _ID: /[A-Za-z_][A-Za-z_0-9]*/
        
        %import common.NUMBER

        %import common.WS
        %ignore WS 
"""

#BitVector Grammar
#(define-fun phi ((k (_ BitVec 3)) (l (_ BitVec 3)) (p0 (_ BitVec 3)) (p1 (_ BitVec 3))) (_ BitVec 3) 
#(let ((_let_0 (X k l p0))) (bvnot (bvimpl (bvimpl p0 (X k l _let_0)) _let_0))))

bv_grammar = r"""

        ?start: bv_fun
        bv_fun: "(define-fun" func_def formula ")"
        func_def: "phi" "(" _vars  ")" _type 
        
        _vars: _vars _var | _var 
         _var: "(" CNAME _type ")" | "(" "k" _type ")" | "(" "l" _type ")"
         
        _type: "(" "_" "BitVec" NUMBER ")"  
        
                 
        ?formula: "(" let_expr ")"
                | "(" _unary_expression ")"
                | "(" _binary_expression ")"
                | variable 
                | constants
        
        let_expr: let_expr formula | "let" "(" let_term ")"
        
        let_term:  "(" CNAME formula ")" 
        _unary_expression: unary_op [_loop_var _loop_var] formula 

        _binary_expression: binary_op [_loop_var _loop_var] formula formula 
        
        !binary_op: "S" | "U" | "bvimpl" | "bvor" | "bvand"
        !unary_op: "Y" | "H" | "O"  | "X" | "F" | "G" | "bvnot"
        !constants: "S_TRUE" | "S_FALSE"
        !variable: CNAME
        _loop_var: "k" | "l"

        CNAME: ("-"|"_"|LETTER) ("-"|"_"|LETTER|DIGIT)*
    
        %import common.LETTER
        %import common.DIGIT
                
        %import common.NUMBER

        %import common.WS
        %ignore WS 
"""

class TreeToFormula(Transformer):
         
        def formula(self, formulaArgs):
            return PLTLFormula(formulaArgs)
        
        def variable(self, varName):
            return PLTLFormula([str(varName[0]), None, None])
        
        def binary_op(self, args):
            return str(args[0])
        
        def unary_op(self, args):
            return str(args[0])
        
class ADTTreeToFormula(Transformer):
         
        def formula(self, formulaArgs):
            return PLTLFormula(formulaArgs)

        def constants(self, varName):
            const = str(varName[0])
            if (const == "Top"):
                const = "TRUE"
            elif (const == "Bottom"):
                const = "FALSE"    
            return PLTLFormula([const, None, None])
        
        def variable(self, number):
            var = 'p'+ number[0]
            return PLTLFormula([var, None, None])
                        
        def binary_op(self, args):
            bop = str(args[0])
            
            if (bop == "AND"):
                bop = "&"
            if (bop == "OR"):
                bop = "|"
            if (bop == "IMPLIES"):
                bop = "=>"    
            return bop
        
        def unary_op(self, args):
            nop = str(args[0])
            if (nop == "NOT"):
                nop = "!"            
            return nop

class BVTree2Fml(Transformer):
        
        t_dict = {} 
        
        def bv_fun(self, formulaArgs):
            return formulaArgs[-1]
        
        def formula(self, formulaArgs):
            return PLTLFormula(formulaArgs)

        def let_expr(self, formulaArgs):
            if len(formulaArgs) > 1:
                return formulaArgs[1]
#            v2 = formulaArgs[1]
#            print('let_expr',expr)
#            print('let_expr',v2)
#            return expr

        def let_term(self, formulaArgs):
            ref_var = formulaArgs[0]
            ref_fml = formulaArgs[1]
            
#            print('ref variable:', ref_var)
#            print('ref formula:', ref_fml)
            BVTree2Fml.t_dict[ref_var] = ref_fml
            return ref_fml
#            return ref_fml

        
        def constants(self, varName):
            const = str(varName[0])
            if (const == "S_TRUE"):
                const = "TRUE"
            elif (const == "S_FALSE"):
                const = "FALSE"    
            return PLTLFormula([const, None, None])
        
        def variable(self, cname):
            var = cname[0]
#            print('var names:',var)
            if '_let_' in var:
                return BVTree2Fml.t_dict[var]
            return PLTLFormula([var, None, None])
                        
        def binary_op(self, args):
            bop = str(args[0])
                        
            if (bop == "bvand"):
                bop = "&"
            elif (bop == "bvor"):
                bop = "|"
            elif (bop == "bvimpl"):
                bop = "=>"

            return bop
        
        def unary_op(self, args):
            nop = str(args[0])
            if (nop == "bvnot"):
                nop = "!"
            
            return nop

class pLTLParser:
    
    
    def parse(self, s_input):
 
        fml = None
        
        parser = Lark(fml_grammar, parser='lalr', lexer='standard', transformer=TreeToFormula())
        
        try:
            fml = parser.parse(s_input)            
            logging.info('Parsed Formula: %s'%(str(fml)))

        except ParseError as e:    
            logging.error('Failed to Parse Formula, error:')
            logging.error(str(e))                
#            quit
            

        return fml   
    
    def parse_adt(self, s_input):
 
        fml = None
        
        parser = Lark(adt_grammar, parser='lalr', lexer='standard', transformer=ADTTreeToFormula())
        
        try:
            fml = parser.parse(s_input)            
        except ParseError as e:    
            logging.error('Failed to Parse LTL Formula, error:')
            logging.error(str(e))                

        return fml   

    def parse_bv(self, s_input):
 
        fml = None
        
        parser = Lark(bv_grammar, parser='lalr', lexer='standard', transformer=BVTree2Fml())
        
        try:
            fml = parser.parse(s_input)            
        except ParseError as e:    
            logging.error('Failed to Parse LTL Formula, error:')
            logging.error(str(e))                
            
        return fml   
  
    def dict_var(self, f, vars_dict):
        
        if f is None:
            return None

        if(f._isLeaf()):
            if f.label == 'TRUE' or f.label == 'FALSE':
                var_name = f.label
            else:                   
                var_name = vars_dict[f.label]
            f = PLTLFormula([var_name, None, None])
            return f
        
        left = self.dict_var(f.left, vars_dict)
        right = self.dict_var(f.right, vars_dict)
        
        return PLTLFormula([f.label, left, right])


if __name__ == "__main__":
#    s_input =     '(define-fun phi ((k (_ BitVec 5)) (l (_ BitVec 5)) (failure (_ BitVec 5)) (alarm (_ BitVec 5))) (_ BitVec 5) (X k l (U k l (G k l S_TRUE) (bvnot (bvimpl alarm failure)))))\n'
    s_input = '(define-fun phi ((k (_ BitVec 3)) (l (_ BitVec 3)) (p0 (_ BitVec 3)) (p1 (_ BitVec 3))) (_ BitVec 3) (let ((_let_0 (X k l p0))) (bvnot (bvimpl (bvimpl p0 (X k l _let_0)) _let_0))))'

    parser = pLTLParser()
    f = parser.parse_bv(s_input)
#    true_fml = PLTLFormula(["TRUE", None, None])
#    ufml  = PLTLFormula(["U", true_fml, f]);
    
    print(f)
#    print(ufml)    