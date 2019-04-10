import numpy as np

import tensorflow as tf 
from tensorflow.python.framework import ops
import keras.backend as K

def minkowski_dot(x, y):
    axes = len(x.shape) - 1, len(y.shape) -1
    return K.batch_dot(x[...,:-1], y[...,:-1], axes=axes) - K.batch_dot(x[...,-1:], y[...,-1:], axes=axes)

def hyperbolic_softmax_loss(sigma=1.):

    def loss(y_true, y_pred, sigma=sigma):

        u_emb = y_pred[:,0]
        samples_emb = y_pred[:,1:]
        
        inner_uv = minkowski_dot(u_emb, samples_emb) 
        inner_uv = -inner_uv - 1. + K.epsilon()#+ 1e-7
        inner_uv = K.maximum(inner_uv, K.epsilon())

        d_uv = tf.acosh(1. + inner_uv) 

        sigma = K.cast(sigma, dtype=K.floatx())
        sigma_sq = K.stop_gradient(sigma ** 2)
        minus_d_uv_sq = - 0.5 * K.square(d_uv) / sigma_sq

        return K.mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y_true[:,0], logits=minus_d_uv_sq)) 

    return loss
