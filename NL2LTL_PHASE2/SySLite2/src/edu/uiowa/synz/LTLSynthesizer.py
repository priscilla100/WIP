'''
Copyright (c) 2020, Board of Trustees of the University of Iowa.
All rights reserved.

Use of this source code is governed by a BSD 3-Clause License that
can be found in the LICENSE file.
'''

from edu.uiowa.alogritms.SATMethod import run_sat_algo, run_enum_sat_algo, run_guided_sat_algo, run_guided_sat_enum_algo
from edu.uiowa.alogritms.DecisionTreeMethod import run_dt_algo, run_scikit_dt_algo
from edu.uiowa.alogritms.SyGuSMethod import run_adt_sygus_algo, run_bv_sygus_algo, run_ltl_bv_sygus_algo
from edu.uiowa.alogritms.SMTMethod import run_adt_fin_algo
from edu.uiowa.utils.FileReader import read_traces_1

import os
import logging


def synthesize_LTL(_size, _count, AP_Lit, _algo_type, solver_type, result_file, trace_file, benign_traces, rejected_traces, unary_operators, binary_operators, _nsize, target_fml, max_trace_length):
    
    if len(unary_operators) == 0 and  len(binary_operators) == 0:
        
        unary_operators =  ['!', 'X']
        binary_operators = ['U','&', '|', '=>']

    logging.debug('*** AP:%s'%(AP_Lit))
    logging.debug('*** +ve Traces Size:%d'%(len(benign_traces)))
    logging.debug('*** -ve Traces Size:%d'%(len(rejected_traces)))
    logging.debug('*** Unary Operators:%s'%(unary_operators))
    logging.debug('*** Binary Operators:%s'%(binary_operators))
    logging.debug('*** Formula Size:%d'%(_size))
    
#    logging.debug(target_fml)
    
        
    logging.info('File: %s'%(trace_file.name))     
    logging.info('+ve Traces: %d'%(len(benign_traces)))
    logging.info('-ve Traces: %d'%(len(rejected_traces)))
    logging.info('Provided Depth/Size: %d'%(_nsize))
    
    _result = []
    
    #SAT Algorithm.
    if _algo_type == 'bv_sygus' :
        def_file = os.path.abspath('resources/ltl-bv-sygus.sy')
        sygus_def_file = open(def_file, 'rt')
        _result = run_ltl_bv_sygus_algo(sygus_def_file, _size, _count, trace_file, benign_traces, rejected_traces, unary_operators, binary_operators, max_trace_length, AP_Lit)

    else:
        logging.warn('Correct Synthesizing algorithm is not selected! -- Please select one')    
    
    if _result == None or len(_result) == 0:
        logging.info('Unable to Synthesize any Formula!')
    else:
        logging.info('Formulas:')
        fml_count = 1
        for synf in _result: 
            synFml = '(%d) %s'%(fml_count, synf)
            
            result_file.write(synFml+'\n')
            logging.info(synFml)
            
            fml_count += 1
        result_file.close()

    if target_fml != None:
        logging.info('Target: %s'%(target_fml))     

    return _result    

