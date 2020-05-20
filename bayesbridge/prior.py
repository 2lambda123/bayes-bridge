import math
import scipy as sp
from scipy.special import polygamma as scipy_polygamma

class RegressionCoefPrior():

    def __init__(
            self, bridge_exponent=None, global_scale_prior_hyper_param=None):
        """

        Parameters
        ----------
        global_scale_prior_hyper_param : dict
            Should contain pair of keys 'log10_mean' and 'log10_sd',
            specifying the prior mean and standard deviation of
            log10(global_scale).
        """
        if global_scale_prior_hyper_param is None:
            self.param = {'gscale_neg_power': {'shape': 0., 'rate': 0.}}
                # Reference prior for a scale family.
        else:
            shape, rate = self.solve_for_gscale_prior_hyperparam(
                global_scale_prior_hyper_param['log10_mean'],
                global_scale_prior_hyper_param['log10_sd'],
                bridge_exponent
            )
            self.param['gscale_neg_power'] = {'shape': shape, 'rate': rate}

    def solve_for_gscale_prior_hyperparam(self, log10_mean, log10_sd, bridge_exp):
        unit_bridge_magnitude \
                = self.compute_power_exp_ave_magnitude(bridge_exp, 1.)
        log_mean = self.change_log_base(log10_mean, from_=10., to=math.e)
        log_sd = self.change_log_base(log10_sd, from_=10., to=math.e)
        if self.global_scale_parametrization == 'coefficient':
            log_mean -= math.log(unit_bridge_magnitude)
        shape, rate = self.solve_for_gamma_param(
            log_mean, log_sd, bridge_exp
        )
        return shape, rate

    @staticmethod
    def compute_power_exp_ave_magnitude(exponent, scale=1.):
        """ Returns the expected absolute value of a random variable with
        density proportional to exp( - |x / scale|^exponent ).
        """
        return scale * math.gamma(2 / exponent) / math.gamma(1 / exponent)

    @staticmethod
    def change_log_base(val, from_=math.e, to=10.):
        return val * math.log(from_) / math.log(to)

    def solve_for_gamma_param(self, log_mean, log_sd, bridge_exp):
        """ Find hyper-parameters matching specified mean and sd in log scale. """

        f = lambda log_shape: (
            math.sqrt(self._polygamma(1, math.exp(log_shape))) / bridge_exp
            - log_sd
        ) # Function whose root coincides with the desired log-shape parameter.
        lower_lim = -10.  # Any sufficiently small number is fine.
        if log_sd < 0:
            raise ValueError("Variance has to be positive.")
        elif log_sd > 10 ** 8:
            raise ValueError("Specified prior variance is too large.")
        lower, upper = self._find_root_bounds(f, lower_lim)

        try:
            log_shape = sp.optimize.brentq(f, lower, upper)
        except BaseException as error:
            print('Solving for the global scale gamma prior hyper-parameters '
                  'failed; {}'.format(error))
        shape = math.exp(log_shape)
        rate = math.exp(
            self._polygamma(0, shape) + bridge_exp * log_mean
        )
        return shape, rate

    @staticmethod
    def _polygamma(n, x):
        """ Wrap the scipy function so that it returns a scalar. """
        return scipy_polygamma([n], x)[0]

    @staticmethod
    def _find_root_bounds(f, init_lower_lim, increment=5., max_lim=None):
        if max_lim is None:
            max_lim = init_lower_lim + 10 ** 4
        if f(init_lower_lim) < 0:
            raise ValueError(
                "Objective function must have positive value "
                "at the lower limit."
            )
        lower_lim = init_lower_lim
        while f(lower_lim + increment) > 0 and lower_lim < max_lim:
            lower_lim += increment
        if lower_lim >= max_lim:
            raise Exception()  # Replace with a warning.
        upper_lim = lower_lim + increment
        return (lower_lim, upper_lim)