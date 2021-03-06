# -*- coding: utf-8 -*-
"""
Created on Fri Oct 31 16:15:43 2014

@author: Ingmar Schuster
"""

from __future__ import division, print_function, absolute_import
from numpy import exp, log, sqrt
from scipy.misc import logsumexp
from scipy.special import multigammaln
from numpy.linalg import inv

import numpy as np
import scipy.stats as stats



def centering_matr(n):
    return np.eye(n) - 1./n * np.ones((n,n))

def scatter_matr(D, observations_in_rows = True):
    if observations_in_rows:
        M = D.T
    else:
        M = D
    return M.dot(centering_matr(M.shape[1])).dot(M.T)

def analytic_postparam_logevidence_mvnorm_unknown_K_li(D, mu_pr, prec_pr, kappa_pr, nu_pr):
    D_mean = np.mean(D, 0)  
    
    (n, dim) = D.shape
    (kappa_post, nu_post) = (kappa_pr + n, nu_pr + n)
    mu_post = (mu_pr * kappa_pr + D_mean * n) / (kappa_pr + n)    
    scatter = scatter_matr(D)
    m_mu_pr = (D_mean - mu_pr)
    m_mu_pr.shape = (1, np.prod(m_mu_pr.shape))
    prec_post = prec_pr + scatter + kappa_pr * n /(kappa_pr + n) * m_mu_pr.T.dot(m_mu_pr)
        
    (sign, ldet_pr) = np.linalg.slogdet(prec_pr)
    (sign, ldet_post) = np.linalg.slogdet(prec_post)
    
    evid = (-(log(np.pi)*n*dim/2)  + multigammaln(nu_post/2, dim)
                                  - multigammaln(nu_pr / 2, dim) 
                                  + ldet_pr * nu_pr/2
                                  - ldet_post * nu_post/2
                                  + dim/2 * (log(kappa_pr) - log(kappa_post))
                                  )

    return ((mu_post, prec_post, kappa_post, nu_post), evid)

def analytic_postparam_logevidence_mvnorm_known_K_li(D, mu_pr, K_pr, K_li):
    Ki_pr = inv(K_pr)
    Ki_li = inv(K_li)
    num_obs = D.shape[0]
    mu_empirical = np.atleast_2d(D.mean(0))
    mu_empirical.shape = (np.prod(mu_empirical.shape),)
    mu_pr.shape = (np.prod(mu_pr.shape),)
    
    Ki_post = Ki_pr + num_obs * Ki_li
    K_post = inv(Ki_post)
    mu_post = K_post.dot(num_obs * Ki_li.dot(mu_empirical) + Ki_pr.dot(mu_pr))
    
    # we compute evidence by a simple application of Bayes rule:
    #    evidence  = prior * likelihood / posterior
    # in other words, for any x we have
    #    p(D) = p(x) * p(D|x) / p(x|D)
    # in the following we arbitrarily use x = mu_post
    evid = (stats.multivariate_normal(mu_pr, K_pr).logpdf(mu_post)    #log prior of mu_post
            + stats.multivariate_normal(mu_post, K_li).logpdf(D).sum()  #log likelihood of mu_post
            - stats.multivariate_normal(mu_post, K_post).logpdf(mu_post)) #analytic log posterior of mu_post
            
    return ((mu_post, K_post, Ki_post), evid)
    

def analytic_logevidence_scalar_gaussian(D, mu_pr, sd_pr, sd_li):
    v_pr = sd_pr**2 #tau^2 in Murphy
    v_li = sd_li**2 #sigma^2 in Murphy
    D_mean = np.mean(D)
    D_mean_sq = D_mean**2
    
    fact = [ (log(sd_li) - ( len(D) *log(sqrt(2*np.pi) *sd_li) #1st factor
                           + log(sqrt(len(D) * v_pr + v_li))   )),
             (- (  np.power(D, 2).sum() / (2 * v_li)   #2nd factor
                 + mu_pr**2             / (2 * v_pr))),
             (( (v_pr*len(D)**2 *D_mean_sq)/v_li   #numerator of 3rd factor
                 + (v_li * D_mean_sq)/v_pr
                 + 2 * len(D) * D_mean * mu_pr
               ) / (2 * (len(D) * v_pr + v_li)) # denominator of 3rd factor
             )            
           ]
    #print(fact)
    return np.sum(fact)

def importance_weights(true_measure, proposal_dist, imp_samp):
    w = (true_measure(imp_samp) # true (not necessarily normalized) measure of sample distribution
         - proposal_dist.logpdf(imp_samp) # log pdf of proposal distribution
         )
    w_norm = w - logsumexp(w)
    return (w, w_norm)

def evidence_from_importance_weights(weights, num_weights_range = None):
    if num_weights_range is None:
        return logsumexp(weights)-log(len(weights))
    return [logsumexp(weights[:N]) - log(N) for N in num_weights_range]