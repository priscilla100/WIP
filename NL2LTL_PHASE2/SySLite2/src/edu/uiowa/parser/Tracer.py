'''
Copyright (c) 2020, Board of Trustees of the University of Iowa.
All rights reserved.

Use of this source code is governed by a BSD 3-Clause License that
can be found in the LICENSE file.
'''

from edu.uiowa.parser.LarkParser import pLTLParser
from edu.uiowa.parser.Formula import PLTLFormula

import logging

class Trace:
    #Adopted the trace format suggested by Daniel Neider & Garvan
    def __init__(self, data, Id, Lit = None):
        self.Id = Id        
#        print('Trace Data:', data, data.find(':'))
        
        lasso_index = data.find(':')
        if(lasso_index != -1):
            self.lasso = int(data[lasso_index+2:])
            data = data[0:lasso_index]            
#            print('Lasso Value>>>>>>>>>>>>>', self.lasso)
#            print('Data >>>>>>>>>>>>>', data)
            
        else:
            self.lasso = 0
        
#        self.loop = False
 
        self.traceVector = [[self.str2bool(var) for var in timeStamp.split(',')] for timeStamp in data.split(';')] 
        self.traceLength = len(self.traceVector)

        self.vars = len(self.traceVector[0])
         
        if Lit is None:
            self.literals = ['p' + str(i) for i in range(self.vars)]
        else:
            self.literals = Lit
            
        self.table = {}

        logging.debug('%s(timestep, var, value)'%(self.Id))        
        for t in range(self.traceLength):                    
            for v in range(self.vars):                                    
                self.table[self.literals[v], t] = self.traceVector[t][v]
                logging.debug('%s(%s, %s:=%s)'%(self.Id, t,self.literals[v],self.table[self.literals[v], t])) 
        
        logging.debug('TruthTable %s'%(self.table))
    
        self.loop = False
    
    def __hash__(self):
        return hash((self.Id, self.traceLength))
            
    def __repr__(self):
        tprint = lambda x: '1' if x else '0'
        return "Trace Id(%s) Lasso(%d) : "%(repr(self.Id),self.lasso) + ';'.join([','.join(map(tprint, l)) for l in self.traceVector]) 
        
    def print_trace(self):
        for t in range(self.traceLength):                    
            for v in range(self.vars):                                    
                self.table[self.literals[v], t] = self.traceVector[t][v]
                logging.debug('%s(%s, %s:=%s)'%(self.Id, t,self.literals[v],self.table[self.literals[v], t])) 

    def truthTable(self, formula):
        nodes = list(set(formula.getAllNodes()))
                    
        self.truthAssignmentTable = {node: [None for _ in range(self.traceLength)] for node in nodes}
        
        for i in range(self.vars):
            fml = PLTLFormula([self.literals[i], None, None])
            self.truthAssignmentTable[fml] = [bool(measurement[i]) for measurement in self.traceVector]
            
        
    def past(self, current):
        pastPos = []
        while current != -1:
            pastPos.append(current)
            current = self.pre(current)
        return pastPos

    def pre(self, pos):
        if (pos == 0):
            return -1;
        else:
            return pos - 1

    def next(self, pos):
        if (pos < self.traceLength - 1):
            return pos + 1
        elif not self.loop:
            self.loop = True
            return self.lasso
        else:
            return -1    

    def next1(self, pos):
        if (pos < self.traceLength - 1):
            return pos + 1
        else:
            return self.lasso

    def check_truth(self, f):
        for index in range(0, self.traceLength):
            if not self.truthValue(f, index):
                return False
        return True

    def check_truth1(self, f):
        self.loop = False
        return self.truthValue(f, 0)
            
    def truthValue(self, f, i):
        
        if(f.label == 'O'):
            var = self.truthValue(f.left, i)
            if i > 0:
                o_var = self.truthValue(f, self.pre(i))
                return var or o_var
            return var                
        elif(f.label == 'H'):
            var = self.truthValue(f.left, i)
            if i > 0:
                h_var = self.truthValue(f, self.pre(i))
                return var and h_var
            return var    
        elif(f.label == '!'):
            var = self.truthValue(f.left, i)
            return not(var)
        elif(f.label == 'Y'):
            if i > 0:
                var = self.truthValue(f.left, self.pre(i))
            else:
                return False
            return var   
        elif(f.label == 'S'):
            g_var = self.truthValue(f.right, i)
            if i > 0:
                var = self.truthValue(f.left, i)
                s_var = self.truthValue(f, self.pre(i))
                return g_var or (var and s_var)    
            return g_var        
        elif(f.label == 'X'):
#            self.loop = False            
            nindex = self.next1(i)
            
            if nindex == -1:
                return False
            else:
                return self.truthValue(f.left, nindex)
            
        elif(f.label == 'U'):
            var_a = self.truthValue(f.left, i)
            var_b = self.truthValue(f.right, i)
            if var_b:
                return True
            elif var_a and not var_b:
                nindex = self.next(i)                
                if nindex == -1:                    
                    return False
                else:
                    return self.truthValue(f, nindex)
            else:
                return False    
        elif(f.label == 'F'):
            fml1 = PLTLFormula(["TRUE", None, None])
            fml2  = PLTLFormula(["U", fml1, f.left]);
            var = self.truthValue(fml2, i)
            return var            
        elif(f.label == 'G'):
            fml1 = PLTLFormula(["!", f.left, None])
            fml2 = PLTLFormula(["F", fml1, None])
            fml3 = PLTLFormula(["!", fml2, None])
            return self.truthValue(fml3, i)
#         elif(f.label == 'G'):
#             var = self.truthValue(f.left, i)
#             if (i < self.traceLength - 1):
#                 g_var = self.truthValue(f, self.next(i))
#                 return var and g_var
#             return var                                 
        elif(f.label == '&'):
            left_var = self.truthValue(f.left, i)
            right_var = self.truthValue(f.right, i)
            return left_var and right_var
        elif(f.label == '=>'):
            left_var = self.truthValue(f.left, i)
            right_var = self.truthValue(f.right, i)
            return not(left_var) or right_var      
        elif(f.label == '|'):
            left_var = self.truthValue(f.left, i)
            right_var = self.truthValue(f.right, i)
            return left_var or right_var
        elif(f.label == 'TRUE'):
            return True
        elif(f.label == 'FALSE'):
            return False
        else:
            if f._isLeaf():                    
                return self.table[f.label,i]
            else:
                print('Trace Evaluator Error -- Unable to found evaluation of atom: ', f.label)
                
                
    def str2bool(self, v):
        return v.lower() in ("yes", "true", "t", "1")        
  
if __name__ == "__main__":
    
    trace = Trace("0,1;1,1;1,1","8", ['p','q'])
    print(trace)
    
    parser = pLTLParser()
    f = parser.parse("G(q)")

    print(f)
    value = trace.check_truth1(f)
    print(value)
        