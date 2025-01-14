"""frd_test.py - test FRD class

RvP, 4 Oct 2012
"""

import sys as pysys

import numpy as np
import matplotlib.pyplot as plt
import pytest

import control as ct
from control.statesp import StateSpace
from control.xferfcn import TransferFunction
from control.frdata import frd, _convert_to_frd, FrequencyResponseData
from control import bdalg, evalfr, freqplot
from control.tests.conftest import slycotonly
from control.exception import pandas_check


class TestFRD:
    """These are tests for functionality and correct reporting of the
    frequency response data class."""

    def testBadInputType(self):
        """Give the constructor invalid input types."""
        with pytest.raises(ValueError):
            frd()
        with pytest.raises(TypeError):
            frd([1])

    def testInconsistentDimension(self):
        with pytest.raises(TypeError):
            frd([1, 1], [1, 2, 3])

    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testSISOtf(self, frd_fcn):
        # get a SISO transfer function
        h = TransferFunction([1], [1, 2, 2])
        omega = np.logspace(-1, 2, 10)
        sys = frd_fcn(h, omega)
        assert isinstance(sys, FrequencyResponseData)

        mag1, phase1, omega1 = sys.frequency_response([1.0])
        mag2, phase2, omega2 = h.frequency_response([1.0])
        np.testing.assert_array_almost_equal(mag1, mag2)
        np.testing.assert_array_almost_equal(phase1, phase2)
        np.testing.assert_array_almost_equal(omega1, omega2)

    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testOperators(self, frd_fcn):
        # get two SISO transfer functions
        h1 = TransferFunction([1], [1, 2, 2])
        h2 = TransferFunction([1], [0.1, 1])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(h1, omega)
        f2 = frd_fcn(h2, omega)

        np.testing.assert_array_almost_equal(
            (f1 + f2).frequency_response(chkpts)[0],
            (h1 + h2).frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            (f1 + f2).frequency_response(chkpts)[1],
            (h1 + h2).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (f1 - f2).frequency_response(chkpts)[0],
            (h1 - h2).frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            (f1 - f2).frequency_response(chkpts)[1],
            (h1 - h2).frequency_response(chkpts)[1])

        # multiplication and division
        np.testing.assert_array_almost_equal(
            (f1 * f2).frequency_response(chkpts)[1],
            (h1 * h2).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (f1 / f2).frequency_response(chkpts)[1],
            (h1 / h2).frequency_response(chkpts)[1])

        # with default conversion from scalar
        np.testing.assert_array_almost_equal(
            (f1 * 1.5).frequency_response(chkpts)[1],
            (h1 * 1.5).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (f1 / 1.7).frequency_response(chkpts)[1],
            (h1 / 1.7).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (2.2 * f2).frequency_response(chkpts)[1],
            (2.2 * h2).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (1.3 / f2).frequency_response(chkpts)[1],
            (1.3 / h2).frequency_response(chkpts)[1])

    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testOperatorsTf(self, frd_fcn):
        # get two SISO transfer functions
        h1 = TransferFunction([1], [1, 2, 2])
        h2 = TransferFunction([1], [0.1, 1])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(h1, omega)
        f2 = frd_fcn(h2, omega)
        f2  # reference to avoid pyflakes error

        np.testing.assert_array_almost_equal(
            (f1 + h2).frequency_response(chkpts)[0],
            (h1 + h2).frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            (f1 + h2).frequency_response(chkpts)[1],
            (h1 + h2).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (f1 - h2).frequency_response(chkpts)[0],
            (h1 - h2).frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            (f1 - h2).frequency_response(chkpts)[1],
            (h1 - h2).frequency_response(chkpts)[1])
        # multiplication and division
        np.testing.assert_array_almost_equal(
            (f1 * h2).frequency_response(chkpts)[1],
            (h1 * h2).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (f1 / h2).frequency_response(chkpts)[1],
            (h1 / h2).frequency_response(chkpts)[1])
        # the reverse does not work

    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testbdalg(self, frd_fcn):
        # get two SISO transfer functions
        h1 = TransferFunction([1], [1, 2, 2])
        h2 = TransferFunction([1], [0.1, 1])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(h1, omega)
        f2 = frd_fcn(h2, omega)

        np.testing.assert_array_almost_equal(
            (bdalg.series(f1, f2)).frequency_response(chkpts)[0],
            (bdalg.series(h1, h2)).frequency_response(chkpts)[0])

        np.testing.assert_array_almost_equal(
            (bdalg.parallel(f1, f2)).frequency_response(chkpts)[0],
            (bdalg.parallel(h1, h2)).frequency_response(chkpts)[0])

        np.testing.assert_array_almost_equal(
            (bdalg.feedback(f1, f2)).frequency_response(chkpts)[0],
            (bdalg.feedback(h1, h2)).frequency_response(chkpts)[0])

        np.testing.assert_array_almost_equal(
            (bdalg.negate(f1)).frequency_response(chkpts)[0],
            (bdalg.negate(h1)).frequency_response(chkpts)[0])

#       append() and connect() not implemented for FRD objects
#        np.testing.assert_array_almost_equal(
#            (bdalg.append(f1, f2)).frequency_response(chkpts)[0],
#            (bdalg.append(h1, h2)).frequency_response(chkpts)[0])
#
#        f3 = bdalg.append(f1, f2, f2)
#        h3 = bdalg.append(h1, h2, h2)
#        Q = np.mat([ [1, 2], [2, -1] ])
#        np.testing.assert_array_almost_equal(
#           (bdalg.connect(f3, Q, [2], [1])).frequency_response(chkpts)[0],
#            (bdalg.connect(h3, Q, [2], [1])).frequency_response(chkpts)[0])

    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testFeedback(self, frd_fcn):
        h1 = TransferFunction([1], [1, 2, 2])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(h1, omega)
        np.testing.assert_array_almost_equal(
            f1.feedback(1).frequency_response(chkpts)[0],
            h1.feedback(1).frequency_response(chkpts)[0])

        # Make sure default argument also works
        np.testing.assert_array_almost_equal(
            f1.feedback().frequency_response(chkpts)[0],
            h1.feedback().frequency_response(chkpts)[0])

    def testFeedback2(self):
        h2 = StateSpace([[-1.0, 0], [0, -2.0]], [[0.4], [0.1]],
                        [[1.0, 0], [0, 1]], [[0.0], [0.0]])
        # h2.feedback([[0.3, 0.2], [0.1, 0.1]])

    def testAuto(self):
        omega = np.logspace(-1, 2, 10)
        f1 = _convert_to_frd(1, omega)
        f2 = _convert_to_frd(np.array([[1, 0], [0.1, -1]]), omega)
        f2 = _convert_to_frd([[1, 0], [0.1, -1]], omega)
        f1, f2  # reference to avoid pyflakes error

    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testNyquist(self, frd_fcn):
        h1 = TransferFunction([1], [1, 2, 2])
        omega = np.logspace(-1, 2, 40)
        f1 = frd_fcn(h1, omega, smooth=True)
        freqplot.nyquist(f1, np.logspace(-1, 2, 100))
        # plt.savefig('/dev/null', format='svg')
        plt.figure(2)
        freqplot.nyquist(f1, f1.omega)
        plt.figure(3)
        freqplot.nyquist(f1)
        # plt.savefig('/dev/null', format='svg')

    @slycotonly
    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testMIMO(self, frd_fcn):
        sys = StateSpace([[-0.5, 0.0], [0.0, -1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[0.0, 0.0], [0.0, 0.0]])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(sys, omega)
        np.testing.assert_array_almost_equal(
            sys.frequency_response(chkpts)[0],
            f1.frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            sys.frequency_response(chkpts)[1],
            f1.frequency_response(chkpts)[1])

    @slycotonly
    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testMIMOfb(self, frd_fcn):
        sys = StateSpace([[-0.5, 0.0], [0.0, -1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[0.0, 0.0], [0.0, 0.0]])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(sys, omega).feedback([[0.1, 0.3], [0.0, 1.0]])
        f2 = frd_fcn(sys.feedback([[0.1, 0.3], [0.0, 1.0]]), omega)
        np.testing.assert_array_almost_equal(
            f1.frequency_response(chkpts)[0],
            f2.frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            f1.frequency_response(chkpts)[1],
            f2.frequency_response(chkpts)[1])

    @slycotonly
    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testMIMOfb2(self, frd_fcn):
        sys = StateSpace(np.array([[-2.0, 0, 0],
                                   [0, -1, 1],
                                   [0, 0, -3]]),
                         np.array([[1.0, 0], [0, 0], [0, 1]]),
                         np.eye(3), np.zeros((3, 2)))
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        K = np.array([[1, 0.3, 0], [0.1, 0, 0]])
        f1 = frd_fcn(sys, omega).feedback(K)
        f2 = frd_fcn(sys.feedback(K), omega)
        np.testing.assert_array_almost_equal(
            f1.frequency_response(chkpts)[0],
            f2.frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            f1.frequency_response(chkpts)[1],
            f2.frequency_response(chkpts)[1])

    @slycotonly
    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testMIMOMult(self, frd_fcn):
        sys = StateSpace([[-0.5, 0.0], [0.0, -1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[0.0, 0.0], [0.0, 0.0]])
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(sys, omega)
        f2 = frd_fcn(sys, omega)
        np.testing.assert_array_almost_equal(
            (f1*f2).frequency_response(chkpts)[0],
            (sys*sys).frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            (f1*f2).frequency_response(chkpts)[1],
            (sys*sys).frequency_response(chkpts)[1])

    @slycotonly
    @pytest.mark.parametrize(
        "frd_fcn", [ct.frd, ct.FRD, ct.FrequencyResponseData])
    def testMIMOSmooth(self, frd_fcn):
        sys = StateSpace([[-0.5, 0.0], [0.0, -1.0]],
                         [[1.0, 0.0], [0.0, 1.0]],
                         [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
                         [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
        sys2 = np.array([[1, 0, 0], [0, 1, 0]]) * sys
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd_fcn(sys, omega, smooth=True)
        f2 = frd_fcn(sys2, omega, smooth=True)
        np.testing.assert_array_almost_equal(
            (f1*f2).frequency_response(chkpts)[0],
            (sys*sys2).frequency_response(chkpts)[0])
        np.testing.assert_array_almost_equal(
            (f1*f2).frequency_response(chkpts)[1],
            (sys*sys2).frequency_response(chkpts)[1])
        np.testing.assert_array_almost_equal(
            (f1*f2).frequency_response(chkpts)[2],
            (sys*sys2).frequency_response(chkpts)[2])

    def testAgainstOctave(self):
        # with data from octave:
        # sys = ss([-2 0 0; 0 -1 1; 0 0 -3],
        #  [1 0; 0 0; 0 1], eye(3), zeros(3,2))
        # bfr = frd(bsys, [1])
        sys = StateSpace(np.array([[-2.0, 0, 0], [0, -1, 1], [0, 0, -3]]),
                         np.array([[1.0, 0], [0, 0], [0, 1]]),
                         np.eye(3), np.zeros((3, 2)))
        omega = np.logspace(-1, 2, 10)
        chkpts = omega[::3]
        f1 = frd(sys, omega)
        np.testing.assert_array_almost_equal(
            (f1.frequency_response([1.0])[0] *
             np.exp(1j * f1.frequency_response([1.0])[1])).reshape(3, 2),
            np.array([[0.4 - 0.2j, 0], [0, 0.1 - 0.2j], [0, 0.3 - 0.1j]]))

    def test_string_representation(self, capsys):
        sys = frd([1, 2, 3], [4, 5, 6])
        print(sys)              # Just print without checking

    def test_frequency_mismatch(self, recwarn):
        # recwarn: there may be a warning before the error!
        # Overlapping but non-equal frequency ranges
        sys1 = frd([1, 2, 3], [4, 5, 6])
        sys2 = frd([2, 3, 4], [5, 6, 7])
        with pytest.raises(NotImplementedError):
            sys = sys1 + sys2

        # One frequency range is a subset of another
        sys1 = frd([1, 2, 3], [4, 5, 6])
        sys2 = frd([2, 3], [4, 5])
        with pytest.raises(NotImplementedError):
            sys = sys1 + sys2

    def test_size_mismatch(self):
        sys1 = frd(ct.rss(2, 2, 2), np.logspace(-1, 1, 10))

        # Different number of inputs
        sys2 = frd(ct.rss(3, 1, 2), np.logspace(-1, 1, 10))
        with pytest.raises(ValueError):
            sys = sys1 + sys2

        # Different number of outputs
        sys2 = frd(ct.rss(3, 2, 1), np.logspace(-1, 1, 10))
        with pytest.raises(ValueError):
            sys = sys1 + sys2

        # Inputs and outputs don't match
        with pytest.raises(ValueError):
            sys = sys2 * sys1

        # Feedback mismatch
        with pytest.raises(ValueError):
            ct.feedback(sys2, sys1)

    def test_operator_conversion(self):
        sys_tf = ct.tf([1], [1, 2, 1])
        frd_tf = frd(sys_tf, np.logspace(-1, 1, 10))
        frd_2 = frd(2 * np.ones(10), np.logspace(-1, 1, 10))

        # Make sure that we can add, multiply, and feedback constants
        sys_add = frd_tf + 2
        chk_add = frd_tf + frd_2
        np.testing.assert_array_almost_equal(sys_add.omega, chk_add.omega)
        np.testing.assert_array_almost_equal(sys_add.fresp, chk_add.fresp)

        sys_radd = 2 + frd_tf
        chk_radd = frd_2 + frd_tf
        np.testing.assert_array_almost_equal(sys_radd.omega, chk_radd.omega)
        np.testing.assert_array_almost_equal(sys_radd.fresp, chk_radd.fresp)

        sys_sub = frd_tf - 2
        chk_sub = frd_tf - frd_2
        np.testing.assert_array_almost_equal(sys_sub.omega, chk_sub.omega)
        np.testing.assert_array_almost_equal(sys_sub.fresp, chk_sub.fresp)

        sys_rsub = 2 - frd_tf
        chk_rsub = frd_2 - frd_tf
        np.testing.assert_array_almost_equal(sys_rsub.omega, chk_rsub.omega)
        np.testing.assert_array_almost_equal(sys_rsub.fresp, chk_rsub.fresp)

        sys_mul = frd_tf * 2
        chk_mul = frd_tf * frd_2
        np.testing.assert_array_almost_equal(sys_mul.omega, chk_mul.omega)
        np.testing.assert_array_almost_equal(sys_mul.fresp, chk_mul.fresp)

        sys_rmul = 2 * frd_tf
        chk_rmul = frd_2 * frd_tf
        np.testing.assert_array_almost_equal(sys_rmul.omega, chk_rmul.omega)
        np.testing.assert_array_almost_equal(sys_rmul.fresp, chk_rmul.fresp)

        sys_rdiv = 2 / frd_tf
        chk_rdiv = frd_2 / frd_tf
        np.testing.assert_array_almost_equal(sys_rdiv.omega, chk_rdiv.omega)
        np.testing.assert_array_almost_equal(sys_rdiv.fresp, chk_rdiv.fresp)

        sys_pow = frd_tf**2
        chk_pow = frd(sys_tf**2, np.logspace(-1, 1, 10))
        np.testing.assert_array_almost_equal(sys_pow.omega, chk_pow.omega)
        np.testing.assert_array_almost_equal(sys_pow.fresp, chk_pow.fresp)

        sys_pow = frd_tf**-2
        chk_pow = frd(sys_tf**-2, np.logspace(-1, 1, 10))
        np.testing.assert_array_almost_equal(sys_pow.omega, chk_pow.omega)
        np.testing.assert_array_almost_equal(sys_pow.fresp, chk_pow.fresp)

        # Assertion error if we try to raise to a non-integer power
        with pytest.raises(ValueError):
            frd_tf**0.5

        # Selected testing on transfer function conversion
        sys_add = frd_2 + sys_tf
        chk_add = frd_2 + frd_tf
        np.testing.assert_array_almost_equal(sys_add.omega, chk_add.omega)
        np.testing.assert_array_almost_equal(sys_add.fresp, chk_add.fresp)

        # Input/output mismatch size mismatch in rmul
        sys1 = frd(ct.rss(2, 2, 2), np.logspace(-1, 1, 10))
        with pytest.raises(ValueError):
            FrequencyResponseData.__rmul__(frd_2, sys1)

        # Make sure conversion of something random generates exception
        with pytest.raises(TypeError):
            FrequencyResponseData.__add__(frd_tf, 'string')

    def test_eval(self):
        sys_tf = ct.tf([1], [1, 2, 1])
        frd_tf = frd(sys_tf, np.logspace(-1, 1, 3))
        np.testing.assert_almost_equal(sys_tf(1j), frd_tf.eval(1))
        np.testing.assert_almost_equal(sys_tf(1j), frd_tf(1j))

        # Should get an error if we evaluate at an unknown frequency
        with pytest.raises(ValueError, match="not .* in frequency list"):
            frd_tf.eval(2)

        # Should get an error if we evaluate at an complex number
        with pytest.raises(ValueError, match="can only accept real-valued"):
            frd_tf.eval(2 + 1j)

        # Should get an error if we use __call__ at real-valued frequency
        with pytest.raises(ValueError, match="only accept purely imaginary"):
            frd_tf(2)

    def test_freqresp_deprecated(self):
        sys_tf = ct.tf([1], [1, 2, 1])
        frd_tf = frd(sys_tf, np.logspace(-1, 1, 3))
        with pytest.warns(FutureWarning):
            frd_tf.freqresp(1.)

    def test_repr_str(self):
        # repr printing
        array = np.array
        sys0 = ct.frd(
            [1.0, 0.9+0.1j, 0.1+2j, 0.05+3j],
            [0.1, 1.0, 10.0, 100.0], name='sys0')
        sys1 = ct.frd(
            sys0.fresp, sys0.omega, smooth=True, name='sys1')
        ref_common = "FrequencyResponseData(\n" \
            "array([[[1.  +0.j , 0.9 +0.1j, 0.1 +2.j , 0.05+3.j ]]]),\n" \
            "array([  0.1,   1. ,  10. , 100. ]),"
        ref0 = ref_common + "\nname='sys0', outputs=1, inputs=1)"
        ref1 = ref_common + " smooth=True," + \
            "\nname='sys1', outputs=1, inputs=1)"
        sysm = ct.frd(
            np.matmul(array([[1], [2]]), sys0.fresp), sys0.omega, name='sysm')

        assert ct.iosys_repr(sys0, format='eval') == ref0
        assert ct.iosys_repr(sys1, format='eval') == ref1

        sys0r = eval(ct.iosys_repr(sys0, format='eval'))
        np.testing.assert_array_almost_equal(sys0r.fresp, sys0.fresp)
        np.testing.assert_array_almost_equal(sys0r.omega, sys0.omega)

        sys1r = eval(ct.iosys_repr(sys1, format='eval'))
        np.testing.assert_array_almost_equal(sys1r.fresp, sys1.fresp)
        np.testing.assert_array_almost_equal(sys1r.omega, sys1.omega)
        assert(sys1._ifunc is not None)

        refs = """<FrequencyResponseData>: {sysname}
Inputs (1): ['u[0]']
Outputs (1): ['y[0]']

Freq [rad/s]  Response
------------  ---------------------
       0.100           1        +0j
       1.000         0.9      +0.1j
      10.000         0.1        +2j
     100.000        0.05        +3j"""
        assert str(sys0) == refs.format(sysname='sys0')
        assert str(sys1) == refs.format(sysname='sys1')

        # print multi-input system
        refm = """<FrequencyResponseData>: sysm
Inputs (2): ['u[0]', 'u[1]']
Outputs (1): ['y[0]']

Input 1 to output 1:

  Freq [rad/s]  Response
  ------------  ---------------------
         0.100           1        +0j
         1.000         0.9      +0.1j
        10.000         0.1        +2j
       100.000        0.05        +3j

Input 2 to output 1:

  Freq [rad/s]  Response
  ------------  ---------------------
         0.100           2        +0j
         1.000         1.8      +0.2j
        10.000         0.2        +4j
       100.000         0.1        +6j"""
        assert str(sysm) == refm

    def test_unrecognized_keyword(self):
        h = TransferFunction([1], [1, 2, 2])
        omega = np.logspace(-1, 2, 10)
        with pytest.raises(TypeError, match="unrecognized keyword"):
            sys = FrequencyResponseData(h, omega, unknown=None)
        with pytest.raises(TypeError, match="unrecognized keyword"):
            sys = ct.frd(h, omega, unknown=None)


def test_named_signals():
    ct.iosys.InputOutputSystem._idCounter = 0
    h1 = TransferFunction([1], [1, 2, 2])
    h2 = TransferFunction([1], [0.1, 1])
    omega = np.logspace(-1, 2, 10)
    f1 = frd(h1, omega)
    f2 = frd(h2, omega)

    # Make sure that systems were properly named
    assert f1.name == 'sys[2]'
    assert f2.name == 'sys[3]'
    assert f1.ninputs == 1
    assert f1.input_labels == ['u[0]']
    assert f1.noutputs == 1
    assert f1.output_labels == ['y[0]']

    # Change names
    f1 = frd(h1, omega, name='mysys', inputs='u0', outputs='y0')
    assert f1.name == 'mysys'
    assert f1.ninputs == 1
    assert f1.input_labels == ['u0']
    assert f1.noutputs == 1
    assert f1.output_labels == ['y0']


@pytest.mark.skipif(not pandas_check(), reason="pandas not installed")
def test_to_pandas():
    # Create a SISO frequency response
    h1 = TransferFunction([1], [1, 2, 2])
    omega = np.logspace(-1, 2, 10)
    resp = frd(h1, omega)

    # Convert to pandas
    df = resp.to_pandas()

    # Check to make sure the data make senses
    np.testing.assert_equal(df['omega'], resp.omega)
    np.testing.assert_equal(df['H_{y[0], u[0]}'], resp.fresp[0, 0])


def test_frequency_response():
    # Create an SISO frequence response
    sys = ct.rss(2, 2, 2)
    omega = np.logspace(-2, 2, 20)
    resp = ct.frequency_response(sys, omega)
    eval = sys(omega*1j)

    # Make sure we get the right answers in various ways
    np.testing.assert_equal(resp.magnitude, np.abs(eval))
    np.testing.assert_equal(resp.phase, np.angle(eval))
    np.testing.assert_equal(resp.omega, omega)

    # Make sure that we can change the properties of the response
    sys = ct.rss(2, 1, 1)
    resp_default = ct.frequency_response(sys, omega)
    mag_default, phase_default, omega_default = resp_default
    assert mag_default.ndim == 1
    assert phase_default.ndim == 1
    assert omega_default.ndim == 1
    assert mag_default.shape[0] == omega_default.shape[0]
    assert phase_default.shape[0] == omega_default.shape[0]

    resp_nosqueeze = ct.frequency_response(sys, omega, squeeze=False)
    mag_nosqueeze, phase_nosqueeze, omega_nosqueeze = resp_nosqueeze
    assert mag_nosqueeze.ndim == 3
    assert phase_nosqueeze.ndim == 3
    assert omega_nosqueeze.ndim == 1
    assert mag_nosqueeze.shape[2] == omega_nosqueeze.shape[0]
    assert phase_nosqueeze.shape[2] == omega_nosqueeze.shape[0]

    # Try changing the response
    resp_def_nosq = resp_default(squeeze=False)
    mag_def_nosq, phase_def_nosq, omega_def_nosq = resp_def_nosq
    assert mag_def_nosq.shape == mag_nosqueeze.shape
    assert phase_def_nosq.shape == phase_nosqueeze.shape
    assert omega_def_nosq.shape == omega_nosqueeze.shape

    resp_nosq_sq = resp_nosqueeze(squeeze=True)
    mag_nosq_sq, phase_nosq_sq, omega_nosq_sq = resp_nosq_sq
    assert mag_nosq_sq.shape == mag_default.shape
    assert phase_nosq_sq.shape == phase_default.shape
    assert omega_nosq_sq.shape == omega_default.shape


def test_signal_labels():
    # Create a system response for a SISO system
    sys = ct.rss(4, 1, 1)
    fresp = ct.frequency_response(sys)

    # Make sure access via strings works
    np.testing.assert_equal(
        fresp.magnitude['y[0]'], fresp.magnitude[0])
    np.testing.assert_equal(
        fresp.phase['y[0]'], fresp.phase[0])

    # Make sure errors are generated if key is unknown
    with pytest.raises(ValueError, match="unknown signal name 'bad'"):
        fresp.magnitude['bad']

    # Create a system response for a MIMO system
    sys = ct.rss(4, 2, 2)
    fresp = ct.frequency_response(sys)

    # Make sure access via strings works
    np.testing.assert_equal(
        fresp.magnitude['y[0]', 'u[1]'],
        fresp.magnitude[0, 1])
    np.testing.assert_equal(
        fresp.phase['y[0]', 'u[1]'],
        fresp.phase[0, 1])
    np.testing.assert_equal(
        fresp.response['y[0]', 'u[1]'],
        fresp.response[0, 1])

    # Make sure access via lists of strings works
    np.testing.assert_equal(
        fresp.response[['y[1]', 'y[0]'], 'u[0]'],
        fresp.response[[1, 0], 0])

    # Make sure errors are generated if key is unknown
    with pytest.raises(ValueError, match="unknown signal name 'bad'"):
        fresp.magnitude['bad']

    with pytest.raises(ValueError, match="unknown signal name 'bad'"):
        fresp.response[['y[1]', 'bad']]

    with pytest.raises(ValueError, match=r"unknown signal name 'y\[0\]'"):
        fresp.response['y[1]', 'y[0]']         # second index = input name
