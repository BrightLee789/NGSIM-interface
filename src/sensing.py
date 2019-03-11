import os
import numpy as np
import pandas as pd
import pickle

from fancyimpute import SoftImpute, KNN
from sklearn.linear_model import LassoCV

from measures import *
from paras import *

class vk_sensing():
  def __init__(self, method, **kwargs):
    self.clf = None
    self.method = method
    if method == "SoftImpute":
      self.clf = SoftImpute(**kwargs)
    elif method == "KNN":
      self.clf = KNN(**kwargs)
    else:
      raise("Not Implemented method")

  def fit_transform(self, X):
    assert(self.clf is not None)
    est_X = self.clf.complete(X)
    return massage_imputed_matrix(est_X)

  def CVfit(self,X, val_ratio = 0.2):
    mask = np.invert(np.isnan(X))
    sample_mask = np.random.rand(*X.shape) < val_ratio
    X_train = X.copy()
    X_train[mask & (~sample_mask)] = np.nan
    X_val = X.copy()
    X_val[mask & (sample_mask)] = np.nan
    cur_best_err = np.inf
    cur_best_k = None
    for k in GLOB_IMPUTE_K_SWEEP:
      clf = construct_low_rank_imputer(self.method, k)
      X_est = massage_imputed_matrix(clf.complete(X_train))
      err = MAE(X_est, X_val)
      # print k, err, RMSN(X_est, X_val)
      if err < cur_best_err:
        cur_best_err = err
        cur_best_k = k
    assert(cur_best_k is not None)
    print cur_best_k
    self.clf = construct_low_rank_imputer(self.method, cur_best_k)

  # def transform(self, X):
  #   assert(self.clf is not None)
  #   clf.transform(X)


class speed_fitting():
  def __init__(self):
    self.clf = None

  def CVfit(self, X_k, X_v):
    X, Y = self._generate_features(X_k, X_v)
    self.clf = LassoCV(cv=5, random_state=0).fit(X, Y)
    print self.clf.score

  def transform(self, X_k, X_v):
    X_mat = self._generate_features(X_k)
    pred_Y = self.clf.predict(X_mat).reshape(*X_k.shape)
    pred_Y[~np.isnan(X_v)] = X_v[~np.isnan(X_v)]
    return pred_Y


  def _generate_features(self, X_k, X_v = None, look_back = 2, space_span = 2):
    available_v_mask = None
    if X_v is not None:
      assert(X_k.shape == X_v.shape)
      available_v_mask = ~np.isnan(X_v)
    else:
      available_v_mask = ~np.isnan(np.zeros_like(X_k))
    X_list = list()
    if X_v is not None:
      Y_list = list()
    for i in range(X_k.shape[0]):
      for j in range(X_k.shape[1]):
        if available_v_mask[i,j]:
          tmp_l = list()
          tmp_l.append(X_k[i,j])
          for t in range(look_back):
            if j - t >= 0:
              tmp_l.append(X_k[i, j-t])
            else:
              tmp_l.append(X_k[i, 0])
          
          for s in range(space_span):
            tmptmp_l = list()
            if i + s < X_k.shape[0]:
              tmptmp_l.append(X_k[i+s, j])
            else:
              tmptmp_l.append(X_k[X_k.shape[0]-1, j])
            if i - s >= 0:
              tmptmp_l.append(X_k[i-s, j])
            else:
              tmptmp_l.append(X_k[0, j])
            tmp_l.append(np.array(tmptmp_l).mean())
          X_list.append(tmp_l)
          if X_v is not None:
            Y_list.append(X_v[i,j])
    if X_v is not None:
      return np.array(X_list).astype(np.float), np.array(Y_list).astype(np.float)
    else:
      return np.array(X_list).astype(np.float)


def construct_low_rank_imputer(method, k):
  clf = None
  if method == "SoftImpute":
    clf = SoftImpute(max_rank = k, verbose = False)
  elif method == "KNN":
    clf = KNN(k = k, verbose = False)
  else:
    raise("Not implemented")
  return clf

def massage_imputed_matrix(X, eps = 1e-3):
  new_X = X.copy()
  for i in range(X.shape[0]):
    tmp = X[i]
    available = np.mean(tmp[tmp > eps])
    for j in range(X.shape[1]):
      if X[i,j] > eps:
        available = X[i,j]
      else:
        new_X[i,j] = available
  return new_X