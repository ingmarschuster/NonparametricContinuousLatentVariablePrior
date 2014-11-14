# -*- coding: utf-8 -*-
"""
Created on Wed Oct 29 13:56:05 2014

@author: Ingmar Schuster
"""

from __future__ import division, print_function, absolute_import
from numpy import exp, log, sqrt
from scipy.misc import logsumexp
import numpy as np
import scipy.stats as stats

def log_sign(a):
    a = np.array(a)
    sign_indicator = ((a < 0 ) * -2 + 1)
    return (log(np.abs(a)), sign_indicator)

def exp_sign(a, sign_indicator):
    return exp(a) * sign_indicator

def logsubtrexp(minuend, subtrahend, sign_minuend = None, sign_subtrahend = None):

    if sign_minuend is None:
        sign_minuend = np.ones(minuend.shape)
    if sign_subtrahend is None:
        sign_subtrahend = np.ones(subtrahend.shape)
    if not (minuend.shape == sign_minuend.shape and subtrahend.shape == sign_subtrahend.shape):
        raise ValueError("sign arguments expected be of same shape as corresponding log-matrices")
    if not (np.abs(sign_minuend).all() and np.abs(sign_subtrahend).all()):
        raise ValueError("sign arguments expected to contain only +1 or -1 elements")
        
    b = np.broadcast(minuend, subtrahend)
    s_b = np.broadcast(sign_minuend, sign_subtrahend)
    abs_res = np.empty(b.shape)
    sign_res = np.empty(b.shape)
    
    for i in range(b.size):
        (m, s) = b.next()
        (sign_m, sign_s) = s_b.next()
        if sign_m > sign_s: # sign_m == 1 and sign_s == -1
            # this is equivalent to logsumexp(m, s)
            #print("sign_m > sign_s")
            sign_res.flat[i] = 1
            abs_res.flat[i] = logsumexp((m,s))
        elif sign_m < sign_s: # sign_m == -1 and sign_s == 1
            #print("sign_m < sign_s")
            sign_res.flat[i] = -1
            abs_res.flat[i] = logsumexp((m,s))
        else:
            #signs are eqal
            if m == s:                
                sign_res.flat[i] = 1
                abs_res.flat[i] = log(0)
            else:
                if sign_m == -1:
                    if m > s:
                        #print("m >= s")
                        sign_res.flat[i] = -1
                        abs_res.flat[i] = log(1 - exp(s - m)) + m
                    elif m < s:
                        #print("m < s")
                        sign_res.flat[i] = 1
                        abs_res.flat[i] = log(1 - exp(m - s)) + s
                else:# sign_m == 1
                    if m > s:
                        #print("m >= s")
                        sign_res.flat[i] = 1
                        abs_res.flat[i] = log(1 - exp(s - m)) + m
                    elif m < s:
                        #print("m < s")
                        sign_res.flat[i] = -1
                        abs_res.flat[i] = log(1 - exp(m - s)) + s
        #print(sign_m*exp(m),  sign_s*exp(s),  sign_m*exp(m) - sign_s*exp(s), sign_res.flat[i] * exp(abs_res.flat[i]))
    
    return (abs_res, sign_res)

def test_logsubtrexp():    
    for (m, s) in [(np.array([[-10.,   3.],[ -1.,   5.]]), np.array([-5.5,  4. ])),
                   (np.array([[10.,   -3.],[ 1.,   -5.]]), np.array([5.5,  -4. ])),
                   (3, 10),
                   (np.arange(3).astype(float), 1),
                   ((np.arange(12).reshape((2,2,3)) - 4).astype(float),1)]:
        (lm, sm) = log_sign(m)
        (ls, ss) = log_sign(s)
        (abs_, sign_) = logsubtrexp(lm, ls, sm, ss)
        assert((np.abs((m - s) - exp_sign(abs_, sign_)) < 1e-14).all())

def logabssubtrexp(minuend, subtrahend, sign_minuend = None, sign_subtrahend = None):
    return logsubtrexp(minuend, subtrahend, sign_minuend, sign_subtrahend)[0]

def logmeanexp(a, sign_indicator = None, axis = None): 
    def conditional_logsumexp(where, axis):
        masked = -np.ones(a.shape) * np.inf
        np.copyto(masked, a, where = where)
        masked_sum = logsumexp(masked, axis = axis)
        #np.copyto(masked_sum,  -np.ones(masked_sum.shape) * np.inf, where = np.isnan(masked_sum)) 
        np.place(masked_sum, np.isnan(masked_sum), -np.inf)
        return masked_sum
    
    a = np.array(a)
    if axis is None:
        norm = log(np.prod(a.shape))
    else:
        norm = log(a.shape[axis])
        
    if sign_indicator is None:
        res = np.array(logsumexp(a, axis = axis)) - norm
        signs = np.ones(res.shape)
    else:
        pos_sum = conditional_logsumexp(sign_indicator == 1, axis)
        neg_sum = conditional_logsumexp(sign_indicator == -1, axis)
        
        #print("axis", axis, "\narray", exp_sign(a, sign_indicator),"\n",(a, sign_indicator), "\npos_sum", pos_sum, "\nneg_sum", neg_sum)
        (res, signs) =  logsubtrexp(pos_sum, neg_sum)
        #np.copyto(res,  -np.ones(res.shape) * np.inf, where = np.isnan(res))
        np.place(res, np.isnan(res), -np.inf)
        res = res - norm
    try:
        sh = list(a.shape)
        sh[axis] = 1
        res = res.reshape(sh)
        signs = signs.reshape(sh)
    except Exception as e:
        print("Exception when trying to reshape:", e)
    return (res, signs)

def test_logmeanexp():
    raise NotImplementedError("check for correct shape!")
    b = np.array([[-10.22911746,   3.68323883],[ -0.41504275,   5.68779   ]])

    for a in (np.array([[ 6.5,  1. ],[ 2.5,  3. ]]),
              np.array([(-10, 3), (-1, 5)]),
              np.arange(4).reshape(2, 2) - 2,
              stats.norm.rvs(0,10, (2,2))):
        (la, sa) = log_sign(a)
        for ax in range(2):
            (abs_, sign_) = logmeanexp(la, sa, ax)
            assert((np.abs(a.mean(ax) - exp_sign(abs_, sign_)) < 1e-10).all())

def logvarexp(a, sign_indicator = None, axis = None):
    # the unbiased estimatior (dividing by (n-1))
    # is only definded for sample sizes >=2)
    assert(a.shape[axis] >= 2) 
    a = np.array(a)
    if axis is None:
        norm = log(np.prod(a.shape))
    else:
        norm = log(a.shape[axis])
    (mean, mean_s) = logmeanexp(a, sign_indicator = sign_indicator, axis = axis)
    (diff, diff_s) = logsubtrexp(a, mean, sign_minuend = sign_indicator, sign_subtrahend = mean_s)
    var = logsumexp(2*diff, axis = axis) - log(diff.shape[axis])
    #ea = exp_sign(a, sign_indicator)
    #emean = exp_sign(mean, mean_s)
    #ediff = exp_sign(diff, diff_s)
    #evar = exp(var)
    #print("=====\n", ea, "\nmean", emean, ea.mean(axis) , "\n diff", ediff, ea -emean, "\nvar",np.var(ea, axis = axis), evar)
    #assert(np.all(np.abs(np.var(ea, axis) - evar) < 1e-10))
    return var

def test_logvarexp():
    b = np.array([[-10.22911746,   3.68323883],[ -0.41504275,   5.68779   ]])

    for a in (np.array([(-10, 3), (-1, 5)]),
              np.arange(4).reshape(2, 2) - 2,
              stats.norm.rvs(0,10, (2,2))):
        (la, sa) = log_sign(a)
        for ax in range(2):
            var_ = logvarexp(la, sa, ax)
            assert((np.abs(np.var(a, ax) - exp(var_)) < 1e-10).all())
    
def log_mse_exp(log_true_theta, log_estimates, axis = 0):
    (diff, sign) = logsubtrexp(log_estimates, log_true_theta)
    return logmeanexp(diff * 2, axis = axis)[0]

def log_bias(log_true_theta, log_estimates, axis = 0):
    assert(log_estimates.shape[axis] == log_true_theta.shape[axis] and
       log_estimates.shape[axis] == np.prod(log_true_theta.shape))
        
    #(true_tiled, log_estimates) = np.broadcast_arrays(log_true_theta, log_estimates)
    (diff, sign) = logsubtrexp(log_estimates, log_true_theta)
    return logmeanexp(diff, sign, axis = axis)

def log_bias_sq(log_true_theta, log_estimates, axis = 0):
    return 2*log_bias(log_true_theta, log_estimates, axis = axis)[0]
    
    
    
    