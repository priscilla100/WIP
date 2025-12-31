'''
Copyright (c) 2020, Board of Trustees of the University of Iowa.
All rights reserved.

Use of this source code is governed by a BSD 3-Clause License that
can be found in the LICENSE file.
'''

import logging

#print the results
def eval_result(_result, benign_traces, rejected_traces, _count):        
    
    fail_safe = 1
    _suspected_result = dict()

        
    for pLTL_fml in _result:

        for trace in benign_traces:
            print('>>>> Trace ID,', trace.Id)
            sat = trace.check_truth(pLTL_fml)
            
            if(sat):
                logging.debug('%d - %s over trace %s is SAT'%(fail_safe, pLTL_fml, trace.Id ))                
            else:
                logging.debug('%d - %s over trace %s is UNSAT'%(fail_safe, pLTL_fml, trace.Id))
                _suspected_result[fail_safe] = (pLTL_fml, trace.Id)

        for trace in rejected_traces:

            sat = trace.check_truth(pLTL_fml)

            if( not sat):
                logging.debug('%d - %s over trace %s is UNSAT'%(fail_safe, pLTL_fml, trace.Id ))                
            else:
                logging.debug('%d - %s over trace %s is SAT'%(fail_safe, pLTL_fml, trace.Id ))                
                _suspected_result[fail_safe] = (pLTL_fml, trace.Id)
                            
            for trace_index in range(trace.traceLength): 
                sat = trace.truthValue(pLTL_fml, trace_index)
                
                if(sat):
                    logging.debug('%s over trace %s is SAT @index(%d)'%(pLTL_fml, trace.Id, trace_index))
                else:
                    logging.debug('%s over trace %s is UNSAT @index(%d)'%(pLTL_fml, trace.Id, trace_index))    
                    
    else:        
        logging.debug('Finished Searching Models!')
    
    cCheck = True        

    for key in _suspected_result.keys():
        fml, traceId = _suspected_result[key]
        logging.warn('(%s) %s fails for Trace %s'%(key,fml, traceId))
        cCheck = False
        
    return cCheck

#print the results
def eval_result1(_result, benign_traces, rejected_traces, _count):        
    
    suspected_results = []
        
    for LTL_fml in _result:

        for trace in benign_traces:
#            print('>>>> Trace ID,', trace.Id)
            sat = trace.check_truth1(LTL_fml)
            
            if(sat):
                logging.debug('%s Positive Trace on line %s is SAT'%(LTL_fml, trace.Id))                
            else:
                logging.warn('%s Positive Trace on line %s is UNSAT'%(LTL_fml, trace.Id))
                suspected_results.append((LTL_fml, trace.Id))
#                logging.debug('Incorrect Eval. %s on Trace ID:%s'%(LTL_fml, trace1.Id))
#                logging.debug('Expected: True \neq ')%(sat)            

        for trace in rejected_traces:

            sat = trace.check_truth1(LTL_fml)
                        
            if( not sat):
                logging.debug('%s Negative Trace on line %s is UNSAT'%(LTL_fml, trace.Id))                
            else:
                logging.warn('%s Negative Trace on line %s is SAT'%(LTL_fml, trace.Id))                
                suspected_results.append((LTL_fml, trace.Id))
#                logging.debug('Incorrect Eval. %s on Trace ID:%s'%(LTL_fml, trace1.Id))
#                logging.debug('Expected: False \neq ')%(sat)            
#             for trace_index in range(trace.traceLength): 
#                 sat = trace.truthValue(pLTL_fml, trace_index)
#                 
#                 if(sat):
#                     logging.debug('%s over trace %s is SAT @index(%d)'%(LTL_fml, trace.Id, trace_index))
#                 else:
#                     logging.debug('%s over trace %s is UNSAT @index(%d)'%(LTL_fml, trace.Id, trace_index))    
                    
    else:        
        logging.debug('Finished Searching Models!')
    
    cCheck = True        

    for sresult in suspected_results:
        (fml, traceId) = sresult
        logging.debug('%s fails for Trace %s'%(fml, traceId))
        cCheck = False
        
    return cCheck


