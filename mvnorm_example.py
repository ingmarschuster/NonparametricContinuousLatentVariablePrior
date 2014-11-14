# -*- coding: utf-8 -*-
"""
Created on Fri Oct 31 16:28:21 2014

@author: Ingmar Schuster
"""

from __future__ import division, print_function, absolute_import
from numpy import exp, log, sqrt
from numpy.linalg import inv
from scipy.misc import logsumexp

import numpy as np
import scipy.stats as stats
import cPickle as pickle

import time

from slice_sampling import slice_sample_all_components

from sobol.sobol_seq import i4_sobol, i4_sobol_generate
import halton
import synthdata
from plotting import plot_var_bias_mse
from evidence import analytic_postparam_logevidence_mvnorm_known_K_li, evidence_from_importance_weights
from distributions import mvnorm, norm_invwishart, invwishart_logpdf, invwishart_rv, invwishart

import estimator_statistics as eststat
from linalg import ensure_array



def sample_params_known_K_li(num_samples, D, prior, K_li):
    rval = []
    mu = ensure_array(prior.rvs())
    def llhood():
        return stats.multivariate_normal.logpdf(D, mu, K_li).sum()
    for i in range(num_samples):
        print("Posterior sample", i)
        slice_sample_all_components(mu, llhood, prior)        
        rval.append(mu.copy())
    return np.array(rval)
    
def sample_params_unknown_K_li(num_samples, D, K_pr, nu_pr, mu_pr, kappa_pr):
    rval_K = []
    rval_mu = []
    K = ensure_array(invwishart_rv(K_pr, nu_pr))
    mu = ensure_array(stats.multivariate_normal(mu_pr, K / kappa_pr).rvs())
    if len(mu.shape) == 0:
        mu = mu.reshape((1, 1))
        K = K.reshape((1, 1))
    def llhood():
        return stats.multivariate_normal.logpdf(D, mu, K).sum()
    for i in range(num_samples):        
        slice_sample_all_components(K, llhood, invwishart(K_pr, nu_pr))
        slice_sample_all_components(mu, llhood, stats.multivariate_normal(mu_pr, K / kappa_pr))
        print("Posterior sample", i)
        rval_K.append(K.copy())
        rval_mu.append(mu.copy())
    return (rval_mu, rval_K)

def importance_weights(D, llhood_func, prior, proposal_dist, imp_samp):
    w = (prior.logpdf(imp_samp) # log prior of samples
         + llhood_func(imp_samp) # log likelihood of samples
         - proposal_dist.logpdf(imp_samp) # log pdf of proposal distribution
         )
    w_norm = w - logsumexp(w)
    return (w, w_norm)

def generate_llhood_func_known_K_li(D, K_li):
    def rval(posterior_samples):
        return np.array([stats.multivariate_normal.logpdf(D, mean, K_li).sum()
                           for mean in posterior_samples])
    return rval

## Dimension of Gaussian ##
dims = 1

## Number of posterior samples to draw ##
num_post_samples = 1000


## Number of (Quasi-)Importance samples and precomputed low discrepancy sequence ##
num_imp_samples = 1000

num_datasets = 50


## Data generation ##
datasets = synthdata.simple_gaussian(dims = dims,
                                     observations_range = range(10,11,10),
                                     num_datasets = num_datasets)

#assert()
## MODEL Likelihood 

# mu_li ~ N(mu_pr, sd_pr)
K_li = np.eye(dims) #+ np.ones((dims,dims))


## MODEL  prior ##

mu_pr = np.zeros(dims)
nu_pr = 5
K_pr = np.eye(dims) * 10
kappa_pr = 5
pr = stats.multivariate_normal(mu_pr, K_pr)


lowdisc_seq_sob = i4_sobol_generate(dims, num_imp_samples + 2, 2).T

estimator_names = ["qis(sobol)","is","priorIs"] #,"qis(halton)"
est = {}
res = {}
num_evid_samp = np.logspace(1, np.log10(num_imp_samples), 15, base=10).astype(int)

for obs_size in datasets:
    est[obs_size] = {"an":[]}
    for estim in estimator_names:
        est[obs_size][estim] = []
    for ds in datasets[obs_size]:
        D = ds["obs"]
        
        ## Sample from and fit gaussians to the posteriors ##
        samp = sample_params_known_K_li(num_post_samples, D,
                                           stats.multivariate_normal(mu_pr, K_pr),
                                           K_li)
        param_fit = mvnorm.fit(samp)
        fit = mvnorm(param_fit[0], param_fit[1])
        
        ## Analytic evidence
        ((mu_post, K_post, Ki_post),
         evid) = analytic_postparam_logevidence_mvnorm_known_K_li(D, mu_pr, K_pr, K_li)
        est[obs_size]["an"].append(evid)
        
        # draw quasi importance samples using the pointwise percent point function
        # (PPF, aka quantile function) where cdf^-1 = ppf
        llhood_func = generate_llhood_func_known_K_li(D, K_li)
        
        (qis_sob_w, qis_sob_w_norm) = importance_weights(D, llhood_func, pr, fit,
                                                         fit.ppf_pointwise(lowdisc_seq_sob))
        est[obs_size]["qis(sobol)"].append(evidence_from_importance_weights(qis_sob_w, num_evid_samp))
        ## draw standard importance samples
        (is_w, is_w_norm) = importance_weights(D, llhood_func, pr, fit,
                                               fit.rvs(num_imp_samples))
        est[obs_size]["is"].append(evidence_from_importance_weights(is_w, num_evid_samp))
        
        
        ## draw importance samples from the prior
        (prior_is_w, prior_is_w_norm) = importance_weights(D, llhood_func, pr, pr,
                                               pr.rvs(num_imp_samples))
        est[obs_size]["priorIs"].append(evidence_from_importance_weights(prior_is_w, num_evid_samp))

    for key in est[obs_size]:
        est[obs_size][key] = np.array(est[obs_size][key])
        
    res[obs_size] = {"bias^2":{}, "var": {}, "mse":{}}
    
    # now calculate bias, variance and mse of estimators when compared
    # to analytic evidence
    for estim in estimator_names:
        estimate = est[obs_size][estim]
        analytic = est[obs_size]["an"].reshape((len(est[obs_size]["an"]), 1))
        
        res[obs_size]["bias^2"][estim] = eststat.log_bias_sq(analytic, estimate, axis = 0).flat[:]
        res[obs_size]["mse"][estim] =  eststat.log_mse_exp(analytic, estimate, axis = 0).flat[:]
        res[obs_size]["var"][estim] =  eststat.logvarexp(estimate, axis = 0).flat[:]



res_file_name = ("MV-Normal_" + str(dims)+"d_"
                 + str(num_datasets) + "_Datasets_"
                 + str(num_post_samples)  + "_McmcSamp_"
                 + str(num_imp_samples) + "_ImpSamp_" + str(time.clock()))
print(res_file_name)
with open("results/" + res_file_name + ".pickle", "wb") as f:
    pickle.dump({"res":res, "#is-samp": num_evid_samp, "est": est}, f)
plot_var_bias_mse(res, log(num_evid_samp), "MV-Normal", num_post_samples, num_imp_samples, dims, outfname = "results/"+res_file_name+".pdf")