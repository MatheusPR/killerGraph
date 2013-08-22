"""
This file holds the functions needed for making a killerGraph

Authors: Chase Coleman, Spencer Lyon

Date: 2013-08-22 10:09:04
"""
from __future__ import division, print_function
from math import sqrt
import numpy as np
from scipy.linalg import solve, eig


def doublej(a1, b1, max_it=50):
    """
    Computes the infinite sum V given by

    .. math::

        V = \sum_{j=0}^{\infty} a1^j b1 a1^j'

    where a1 and b1 are each (n X n) matrices with eigenvalues whose
    moduli are bounded by unity and b1 is an (n X n) matrix.

    V is computed by using the following 'doubling algorithm'. We
    iterate to convergence on V(j) on the following recursions for
    j = 1, 2, ... starting from V(0) = b1:

    ..math::

        a1_j = a1_{j-1} a1_{j-1}
        V_j = V_{j-1} + A_{j-1} V_{j-1} a_{j-1}'

    The limiting value is returned in V
    """
    alpha0 = a1
    gamma0 = b1

    diff = 5
    n_its = 1

    while diff > 1e-15:

        alpha1 = alpha0.dot(alpha0)
        gamma1 = gamma0 + np.dot(alpha0.dot(gamma0), alpha0.T)

        diff = np.max(np.abs(gamma1 - gamma0))
        alpha0 = alpha1
        gamma0 = gamma1

        n_its += 1

        if n_its > max_it:
            raise ValueError('Exceeded maximum iterations of %i.' % (max_it) +
                             ' Check your input matrices')

    return gamma1


def doubleo(A, C, Q, R, tol=1e-15):
    """
    This function uses the "doubling algorithm" to solve the Riccati
    matrix difference equations associated with the Kalman filter.  The
    returns the gain K and the stationary covariance matrix of the
    one-step ahead errors in forecasting the state.

    The function creates the Kalman filter for the following system:

    .. math::

        x_{t+1} = A * x_t + e_{t+1}

        y_t = C * x_t + v_t

    where :math:`E e_{t+1} e_{t+1}' =  Q`, and :math:`E v_t v_t' = R`,
    and :math:`v_s' e_t = 0 \\forall s, t`.

    The function creates the observer system

    .. math::

        xx_{t+1} = A xx_t + K a_t

        y_t = C xx_t + a_t

    where K is the Kalman gain, :math:`S = E (x_t - xx_t)(x_t - xx_t)'`,
    and :math:`a_t = y_t - E[y_t| y_{t-1}, y_{t-2}, \dots ]`, and
    :math:`xx_t = E[x_t|y_{t-1},\dots]`.

    Parameters
    ----------
    A : array_like, dtype=float, shape=(n, n)
        The matrix A in the law of motion for x

    C : array_like, dtype=float, shape=(k, n)

    Q : array_like, dtype=float, shape=(n, n)

    R : array_like, dtype=float, shape=(k, k)

    tol : float, optional(default=1e-15)

    Returns
    -------
    K : array_like, dtype=float
        The Kalman gain K

    S : array_like, dtype=float
        The stationary covariance matrix of the one-step ahead errors
        in forecasting the state.

    Notes
    -----
    By using DUALITY, control problems can also be solved.
    """
    a0 = A.T
    b0 = C.T.dot(solve(R, C))
    g0 = Q
    dd = 1
    ss = max(A.shape)
    v = np.eye(ss)

    while dd > tol:
        a1 = a0.dot(solve(v + np.dot(b0, g0), a0))
        b1 = b0 + a0.dot(solve(v + np.dot(b0, g0), b0.dot(a0.T)))
        g1 = g0 + np.dot(a0.T.dot(g0), solve(v + b0.dot(g0), a0))
        k1 = np.dot(A.dot(g1), solve(np.dot(C, g1.T).dot(C.T) + R.T, C).T)
        k0 = np.dot(A.dot(g0), solve(np.dot(C, g0.T).dot(C.T) + R.T, C).T)
        a0 = a1
        b0 = b1
        g0 = g1
        dd = np.max(k1 - k0)

    return k1, g1


def olrp(beta, A, B, Q, R, W=None, tol=1e-6, max_iter=1000):
    """
    Calculates F of the feedback law:

    .. math::

          U = -Fx

     that maximizes the function:

     .. math::

        \sum \{beta^t [x'Qx + u'Ru +2x'Wu] \}

     subject to

     .. math::
          x_{t+1} = A x_t + B u_t

    where x is the nx1 vector of states, u is the kx1 vector of controls

    Parameters
    ----------
    beta : float
        The discount factor from above. If there is no discounting, set
        this equal to 1.

    A : array_like, dtype=float, shape=(n, n)
        The matrix A in the law of motion for x

    B : array_like, dtype=float, shape=(n, k)
        The matrix B in the law of motion for x

    Q : array_like, dtype=float, shape=(n, n)
        The matrix Q from the objective function

    R : array_like, dtype=float, shape=(k, k)
        The matrix R from the objective function

    W : array_like, dtype=float, shape=(n, k), optional(default=0)
        The matrix W from the objective function. Represents the cross
        product terms.

    tol : float, optional(default=1e-6)
        Convergence tolerance for case when largest eigenvalue is below
        1e-5 in modulus

    max_iter : int, optional(default=1000)
        The maximum number of iterations the function will allow before
        stopping

    Returns
    -------
    F : array_like, dtype=float
        The feedback law from the equation above.

    P : array_like, dtype=float
        The steady-state solution to the associated discrete matrix
        Riccati equation

    """
    m = max(A.shape)
    rc, cb = np.atleast_2d(B).shape

    if W is None:
        W = np.zeros((m, cb))

    if np.max(np.abs(eig(R)[0])) > 1e-5:
        A = sqrt(beta) * (A - B.dot(solve(R, W.T)))
        B = sqrt(beta) * B
        Q = Q - W.dot(solve(R, W.T))

        k, s = doubleo(A.T, B.T, Q, R)

        f = k.T + solve(R, W.T)

        p = s

    else:
        p0 = -0.1 * np.eye(m)
        dd = 1
        it = 1

        for it in range(max_iter):
            f0 = solve(R + beta * B.T.dot(p0).dot(B),
                       beta * B.T.dot(p0).dot(A) + W.T)
            p1 = beta * A.T.dot(p0).dot(A) + Q - \
                (beta * A.T.dot(p0).dot(B) + W).dot(f0)
            f1 = solve(R + beta * B.T.dot(p1).dot(B),
                       beta * B.T.dot(p1).dot(A) + W.T)
            dd = np.max(f1 - f0)
            p0 = p1

            if dd > tol:
                break
        else:
            msg = 'No convergence: Iteration limit of {0} reached in OLRP'
            raise ValueError(msg.format(max_iter))

        f = f1
        p = p1

    return f, p