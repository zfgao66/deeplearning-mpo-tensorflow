import tensorflow as tf
import numpy as np
import math
from .auxx import get_var_wrap

def tt_dev(inp,
           inp_modes,
           out_modes,
           mat_ranks,
           cores_initializer=tf.contrib.layers.xavier_initializer(uniform=False),
           cores_regularizer=None,
           biases_initializer=tf.zeros_initializer,
           biases_regularizer=None,
           trainable=True,
           cpu_variables=False,
           scope=None):
    """ tt-layer (tt-matrix by full tensor product)
    Args:
        inp: input tensor, float - [batch_size, prod(inp_modes)]
        inp_modes: input tensor modes
        out_modes: output tensor modes
        mat_ranks: tt-matrix ranks
        cores_initializer: cores init function, could be a list of functions for specifying different function for each core
        cores_regularizer: cores regularizer function, could be a list of functions for specifying different function for each core
        biases_initializer: biases init function (if None then no biases will be used)
        biases_regularizer: biases regularizer function        
        trainable: trainable variables flag, bool
        cpu_variables: cpu variables flag, bool
        scope: layer variable scope name, string
    Returns:
        out: output tensor, float - [batch_size, prod(out_modes)]
    """
    with tf.variable_scope(scope):
        dim = inp_modes.size
        
        mat_cores = []
        
        for i in range(dim):
            if type(cores_initializer) == list:
                cinit = cores_initializer[i]
            else:
                cinit = cores_initializer
            
            if type(cores_regularizer) == list:
                creg = cores_regularizer[i]
            else:
                creg = cores_regularizer

            inp_size = np.prod(inp_modes)
            out_size = np.prod(out_modes)
            x = math.sqrt(6.0 / (inp_size*out_size))
            sigma = math.sqrt(2.0 / (inp_size*out_size))
            tempI = np.ndarray(shape=(out_modes[i], mat_ranks[i + 1], mat_ranks[i], inp_modes[i]),dtype='float32')
            for j in range(mat_ranks[i + 1]):
                for k in range(mat_ranks[i]):
                    # tempI[:, j, k, :] = np.eye(out_modes[i], inp_modes[i]) / math.sqrt(mat_ranks[i + 1]*mat_ranks[i]) + np.random.uniform(low=-x,high=x,size=[out_modes[i], inp_modes[i]])
                    tempI[:, j, k, :] = (np.eye(out_modes[i], inp_modes[i]) + np.random.normal(0.0, sigma,[out_modes[i], inp_modes[i]])) / math.sqrt(mat_ranks[i + 1] * mat_ranks[i])
            tempI = np.reshape(tempI, [ out_modes[i] * mat_ranks[i + 1], mat_ranks[i] * inp_modes[i] ])

            mat_cores.append(get_var_wrap('mat_core_%d' % (i + 1),
                                          shape=None,
                                          initializer=tempI,
                                          regularizer=creg,
                                          trainable=trainable,
                                          cpu_variable=cpu_variables))

        # inp(b,n0,n1,...,nL-1), b: batch_size
        out = tf.reshape(inp, [-1, np.prod(inp_modes)]) # out(b,(n0,n1,...,nL-1))
        out = tf.transpose(out, [1, 0]) # inp((n0,n1,...,nL-1),b)
        
        for i in range(dim):
            # out((ri,ni),(ni+1,...,nL-1,b,m0,...mi-1))
            out = tf.reshape(out, [mat_ranks[i] * inp_modes[i], -1])
            # out[(mi,ri+1),(ni+1,...,nL-1,m0,...mi-1,b)] =
            # mat_cores_i[(mi,ri+1),(ri,ni)] * out((ri,ni),(ni+1,...,nL-1,b,m0,...mi-1))
            out = tf.matmul(mat_cores[i], out)
            # out[mi,(ri+1,ni+1,...,nL-1,b,m0,...mi-1)]
            out = tf.reshape(out, [out_modes[i], -1])
            # out[(ri+1,ni+1,...,nL-1,b,m0,...mi-1),mi]
            out = tf.transpose(out, [1, 0])        
        
        if biases_initializer is not None:
            
            biases = get_var_wrap('biases',
                                  shape=[np.prod(out_modes)],
                                  initializer=biases_initializer,
                                  regularizer=biases_regularizer,
                                  trainable=trainable,
                                  cpu_variable=cpu_variables)
                                                                    
            out = tf.add(tf.reshape(out, [-1, np.prod(out_modes)]), biases, name="out")
        else:
            out = tf.reshape(out, [-1, np.prod(out_modes)], name="out")

    return out
