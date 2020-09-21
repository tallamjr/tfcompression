# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests of deep factorized distribution."""

import tensorflow.compat.v2 as tf
import tensorflow_probability as tfp

from tensorflow_compression.python.distributions import deep_factorized
from tensorflow_compression.python.distributions import helpers


class DeepFactorizedTest(tf.test.TestCase):

  def test_can_instantiate_scalar(self):
    df = deep_factorized.DeepFactorized()
    self.assertEqual(df.batch_shape, ())
    self.assertEqual(df.event_shape, ())
    self.assertEqual(df.num_filters, (3, 3))
    self.assertEqual(df.init_scale, 10)

  def test_can_instantiate_batched(self):
    df = deep_factorized.DeepFactorized(batch_shape=(4, 3))
    self.assertEqual(df.batch_shape, (4, 3))
    self.assertEqual(df.event_shape, ())
    self.assertEqual(df.num_filters, (3, 3))
    self.assertEqual(df.init_scale, 10)

  def test_logistic_is_special_case_prob(self):
    # With no hidden units, the density should collapse to a logistic
    # distribution.
    df = deep_factorized.DeepFactorized(num_filters=(), init_scale=1)
    logistic = tfp.distributions.Logistic(loc=-df._biases[0][0, 0], scale=1.)
    x = tf.linspace(-5., 5., 20)
    prob_df = df.prob(x)
    prob_logistic = logistic.prob(x)
    self.assertAllClose(prob_df, prob_logistic)

  def test_logistic_is_special_case_cdf(self):
    # With no hidden units, the density should collapse to a logistic
    # distribution.
    df = deep_factorized.DeepFactorized(num_filters=(), init_scale=1)
    logistic = tfp.distributions.Logistic(loc=-df._biases[0][0, 0], scale=1.)
    x = tf.linspace(-5., 5., 20)
    cdf_df = df.cdf(x)
    cdf_logistic = logistic.cdf(x)
    self.assertAllClose(cdf_df, cdf_logistic)

  def test_logistic_is_special_case_log_prob(self):
    # With no hidden units, the density should collapse to a logistic
    # distribution.
    df = deep_factorized.DeepFactorized(num_filters=(), init_scale=1)
    logistic = tfp.distributions.Logistic(loc=-df._biases[0][0, 0], scale=1.)
    x = tf.linspace(-5000., 5000., 1000)
    log_prob_df = df.log_prob(x)
    log_prob_logistic = logistic.log_prob(x)
    self.assertAllClose(log_prob_df, log_prob_logistic)

  def test_logistic_is_special_case_log_cdf(self):
    # With no hidden units, the density should collapse to a logistic
    # distribution.
    df = deep_factorized.DeepFactorized(num_filters=(), init_scale=1)
    logistic = tfp.distributions.Logistic(loc=-df._biases[0][0, 0], scale=1.)
    x = tf.linspace(-5000., 5000., 1000)
    log_cdf_df = df.log_cdf(x)
    log_cdf_logistic = logistic.log_cdf(x)
    self.assertAllClose(log_cdf_df, log_cdf_logistic)

  def test_logistic_is_special_case_log_survival_function(self):
    # With no hidden units, the density should collapse to a logistic
    # distribution.
    df = deep_factorized.DeepFactorized(num_filters=(), init_scale=1)
    logistic = tfp.distributions.Logistic(loc=-df._biases[0][0, 0], scale=1.)
    x = tf.linspace(-5000., 5000., 1000)
    log_survival_function_df = df.log_survival_function(x)
    log_survival_function_logistic = logistic.log_survival_function(x)
    self.assertAllClose(log_survival_function_df,
                        log_survival_function_logistic)


class NoisyDeepFactorizedTest(tf.test.TestCase):

  def test_can_instantiate_and_run_scalar(self):
    df = deep_factorized.NoisyDeepFactorized(num_filters=(2, 3, 4))
    self.assertEqual(df.batch_shape, ())
    self.assertEqual(df.event_shape, ())
    self.assertEqual(df.base.num_filters, (2, 3, 4))
    self.assertEqual(df.base.init_scale, 10)
    x = tf.random.normal((10,))
    df.prob(x)

  def test_can_instantiate_and_run_batched(self):
    df = deep_factorized.NoisyDeepFactorized(batch_shape=(4, 3))
    self.assertEqual(df.batch_shape, (4, 3))
    self.assertEqual(df.event_shape, ())
    self.assertEqual(df.base.num_filters, (3, 3))
    self.assertEqual(df.base.init_scale, 10)
    x = tf.random.normal((10, 4, 3))
    df.prob(x)

  def test_variables_receive_gradients(self):
    df = deep_factorized.NoisyDeepFactorized()
    with tf.GradientTape() as tape:
      x = tf.random.normal([20])
      loss = -tf.reduce_mean(df.log_prob(x))
    grads = tape.gradient(loss, df.trainable_variables)
    self.assertLen(grads, 8)
    self.assertNotIn(None, grads)

  def test_logistic_is_special_case(self):
    # With no hidden units, the density should collapse to a logistic
    # distribution convolved with a standard uniform distribution.
    df = deep_factorized.NoisyDeepFactorized(num_filters=(), init_scale=1)
    logistic = tfp.distributions.Logistic(loc=-df.base._biases[0][0, 0],
                                          scale=1.)
    x = tf.linspace(-5., 5., 20)
    prob_df = df.prob(x)
    prob_log = logistic.cdf(x + .5) - logistic.cdf(x - .5)
    self.assertAllClose(prob_df, prob_log)

  def test_uniform_is_special_case(self):
    # With the scale parameter going to zero, the density should approach a
    # unit-width uniform distribution.
    df = deep_factorized.NoisyDeepFactorized(init_scale=1e-3)
    x = tf.linspace(-1., 1., 10)
    self.assertAllClose(df.prob(x), [0, 0, 0, 1, 1, 1, 1, 0, 0, 0])

  def test_quantization_offset_is_zero(self):
    df = deep_factorized.NoisyDeepFactorized()
    self.assertEqual(helpers.quantization_offset(df), 0)

  def test_tails_and_offset_are_in_order(self):
    df = deep_factorized.NoisyDeepFactorized()
    offset = helpers.quantization_offset(df)
    lower_tail = helpers.lower_tail(df, 2**-8)
    upper_tail = helpers.upper_tail(df, 2**-8)
    self.assertGreater(upper_tail, offset)
    self.assertGreater(offset, lower_tail)

  def test_stats_throw_error(self):
    df = deep_factorized.NoisyDeepFactorized()
    with self.assertRaises(NotImplementedError):
      df.mode()
    with self.assertRaises(NotImplementedError):
      df.mean()
    with self.assertRaises(NotImplementedError):
      df.quantile(.5)
    with self.assertRaises(NotImplementedError):
      df.survival_function(.5)
    with self.assertRaises(NotImplementedError):
      df.sample()


if __name__ == "__main__":
  tf.test.main()
