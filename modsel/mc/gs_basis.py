from __future__ import absolute_import, division, print_function
import numpy as np
 
def gs(X, row_vecs=True, norm = True):
    if not row_vecs:
        X = X.T
    Y = X[0:1,:].copy()
    for i in range(1, X.shape[0]):
        proj = np.diag((X[i,:].dot(Y.T)/np.linalg.norm(Y,axis=1)**2).flat).dot(Y)
        Y = np.vstack((Y, X[i,:] - proj.sum(0)))
    if norm:
        Y = np.diag(1/np.linalg.norm(Y,axis=1)).dot(Y)
    if row_vecs:
        return Y
    else:
        return Y.T

def scalar_projection(from_vec, onto_vec):
    # scalar_projection( np.ones(2),np.array((0,1)))

    assert(from_vec.size == onto_vec.size)
    return from_vec.flatten().dot(onto_vec.flatten())/np.linalg.norm(onto_vec)

def test_scalar_projection():
    assert(scalar_projection( np.ones(2),np.array((0,1))) == 1)
    assert(scalar_projection( np.ones(2)*2,np.array((0,1))) == 2)
    assert(np.array(scalar_projection( np.ones(2)*2,np.array((0,1)))).size == 1)



def ideal_covar(direction, main_var_scale = 1, other_var = 0.5, fix_main_var=None):
    direction = direction.flat[:]
    if fix_main_var is not None:
        var = fix_main_var
    else:
        var = np.linalg.norm(direction)*main_var_scale
    vs = np.vstack([direction.flat[:], np.eye(len(direction))[:-1,:]])
    bas = gs(vs)
    ew = np.eye(len(direction))*other_var
    ew[0,0] = var
    return bas.T.dot(ew).dot(np.linalg.inv(bas.T))