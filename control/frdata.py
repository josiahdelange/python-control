# frdata.py - frequency response data representation and functions
#
# Author: M.M. (Rene) van Paassen (using xferfcn.py as basis)
# Date: 02 Oct 12

"""
Frequency response data representation and functions.

This module contains the FRD class and also functions that operate on
FRD data.
"""

from copy import copy
from warnings import warn

import numpy as np
from numpy import absolute, angle, array, empty, eye, imag, linalg, ones, \
    real, sort, where
from scipy.interpolate import splev, splprep

from . import config
from .exception import pandas_check
from .iosys import InputOutputSystem, _process_iosys_keywords, common_timebase
from .lti import LTI, _process_frequency_response

__all__ = ['FrequencyResponseData', 'FRD', 'frd']


class FrequencyResponseData(LTI):
    """FrequencyResponseData(d, w[, smooth])

    A class for models defined by frequency response data (FRD).

    The FrequencyResponseData (FRD) class is used to represent systems in
    frequency response data form.  It can be created manually using the
    class constructor, using the :func:~~control.frd` factory function
    (preferred), or via the :func:`~control.frequency_response` function.

    Parameters
    ----------
    d : 1D or 3D complex array_like
        The frequency response at each frequency point.  If 1D, the system is
        assumed to be SISO.  If 3D, the system is MIMO, with the first
        dimension corresponding to the output index of the FRD, the second
        dimension corresponding to the input index, and the 3rd dimension
        corresponding to the frequency points in omega
    w : iterable of real frequencies
        List of frequency points for which data are available.
    sysname : str or None
        Name of the system that generated the data.
    smooth : bool, optional
        If ``True``, create an interpolation function that allows the
        frequency response to be computed at any frequency within the range of
        frequencies give in ``w``.  If ``False`` (default), frequency response
        can only be obtained at the frequencies specified in ``w``.

    Attributes
    ----------
    ninputs, noutputs : int
        Number of input and output variables.
    omega : 1D array
        Frequency points of the response.
    fresp : 3D array
        Frequency response, indexed by output index, input index, and
        frequency point.
    dt : float, True, or None
        System timebase.

    See Also
    --------
    frd

    Notes
    -----
    The main data members are 'omega' and 'fresp', where 'omega' is a 1D array
    of frequency points and and 'fresp' is a 3D array of frequency responses,
    with the first dimension corresponding to the output index of the FRD, the
    second dimension corresponding to the input index, and the 3rd dimension
    corresponding to the frequency points in omega.  For example,

    >>> frdata[2,5,:] = numpy.array([1., 0.8-0.2j, 0.2-0.8j])   # doctest: +SKIP

    means that the frequency response from the 6th input to the 3rd output at
    the frequencies defined in omega is set to the array above, i.e. the rows
    represent the outputs and the columns represent the inputs.

    A frequency response data object is callable and returns the value of the
    transfer function evaluated at a point in the complex plane (must be on
    the imaginary access).  See :meth:`~control.FrequencyResponseData.__call__`
    for a more detailed description.

    """
    #
    # Class attributes
    #
    # These attributes are defined as class attributes so that they are
    # documented properly.  They are "overwritten" in __init__.
    #

    #: Number of system inputs.
    #:
    #: :meta hide-value:
    ninputs = 1

    #: Number of system outputs.
    #:
    #: :meta hide-value:
    noutputs = 1

    _epsw = 1e-8                #: Bound for exact frequency match

    def __init__(self, *args, **kwargs):
        """Construct an FRD object.

        The default constructor is FRD(d, w), where w is an iterable of
        frequency points, and d is the matching frequency data.

        If d is a single list, 1D array, or tuple, a SISO system description
        is assumed. d can also be

        To call the copy constructor, call FRD(sys), where sys is a
        FRD object.

        To construct frequency response data for an existing LTI
        object, other than an FRD, call FRD(sys, omega).

        """
        # TODO: discrete-time FRD systems?
        smooth = kwargs.pop('smooth', False)

        #
        # Process positional arguments
        #
        if len(args) == 2:
            if not isinstance(args[0], FRD) and isinstance(args[0], LTI):
                # not an FRD, but still a system, second argument should be
                # the frequency range
                otherlti = args[0]
                self.omega = sort(np.asarray(args[1], dtype=float))
                # calculate frequency response at my points
                if otherlti.isctime():
                    s = 1j * self.omega
                    self.fresp = otherlti(s, squeeze=False)
                else:
                    z = np.exp(1j * self.omega * otherlti.dt)
                    self.fresp = otherlti(z, squeeze=False)
                arg_dt = otherlti.dt

            else:
                # The user provided a response and a freq vector
                self.fresp = array(args[0], dtype=complex, ndmin=1)
                if self.fresp.ndim == 1:
                    self.fresp = self.fresp.reshape(1, 1, -1)
                self.omega = array(args[1], dtype=float, ndmin=1)
                if self.fresp.ndim != 3 or self.omega.ndim != 1 or \
                        self.fresp.shape[-1] != self.omega.shape[-1]:
                    raise TypeError(
                        "The frequency data constructor needs a 1-d or 3-d"
                        " response data array and a matching frequency vector"
                        " size")
                arg_dt = None

        elif len(args) == 1:
            # Use the copy constructor.
            if not isinstance(args[0], FRD):
                raise TypeError(
                    "The one-argument constructor can only take in"
                    " an FRD object.  Received %s." % type(args[0]))
            self.omega = args[0].omega
            self.fresp = args[0].fresp
            arg_dt = args[0].dt

        else:
            raise ValueError(
                "Needs 1 or 2 arguments; received %i." % len(args))

        #
        # Process keyword arguments
        #

        # If data was generated by a system, keep track of that (used when
        # plotting data).  Otherwise, use the system name, if given.
        self.sysname = kwargs.pop('sysname', kwargs.get('name', None))

        # Keep track of default properties for plotting
        self.plot_phase = kwargs.pop('plot_phase', None)
        self.title = kwargs.pop('title', None)
        self.plot_type = kwargs.pop('plot_type', 'bode')

        # Keep track of return type
        self.return_magphase=kwargs.pop('return_magphase', False)
        if self.return_magphase not in (True, False):
            raise ValueError("unknown return_magphase value")
        self._return_singvals=kwargs.pop('_return_singvals', False)

        # Determine whether to squeeze the output
        self.squeeze=kwargs.pop('squeeze', None)
        if self.squeeze not in (None, True, False):
            raise ValueError("unknown squeeze value")

        # Process iosys keywords
        defaults = {
            'inputs': self.fresp.shape[1], 'outputs': self.fresp.shape[0],
            'dt': None}
        name, inputs, outputs, states, dt = _process_iosys_keywords(
                kwargs, defaults, end=True)
        dt = common_timebase(dt, arg_dt)        # choose compatible timebase

        # Process signal names
        InputOutputSystem.__init__(
            self, name=name, inputs=inputs, outputs=outputs, dt=dt)

        # create interpolation functions
        if smooth:
            self.ifunc = empty((self.fresp.shape[0], self.fresp.shape[1]),
                               dtype=tuple)
            for i in range(self.fresp.shape[0]):
                for j in range(self.fresp.shape[1]):
                    self.ifunc[i, j], u = splprep(
                        u=self.omega, x=[real(self.fresp[i, j, :]),
                                         imag(self.fresp[i, j, :])],
                        w=1.0/(absolute(self.fresp[i, j, :]) + 0.001), s=0.0)
        else:
            self.ifunc = None

    #
    # Frequency response properties
    #
    # Different properties of the frequency response that can be used for
    # analysis and characterization.
    #

    @property
    def magnitude(self):
        return np.abs(self.fresp)

    @property
    def phase(self):
        return np.angle(self.fresp)

    @property
    def frequency(self):
        return self.omega

    @property
    def response(self):
        return self.fresp

    def __str__(self):
        """String representation of the transfer function."""

        mimo = self.ninputs > 1 or self.noutputs > 1
        outstr = [f"{InputOutputSystem.__str__(self)}"]

        for i in range(self.ninputs):
            for j in range(self.noutputs):
                if mimo:
                    outstr.append("Input %i to output %i:" % (i + 1, j + 1))
                outstr.append('Freq [rad/s]  Response')
                outstr.append('------------  ---------------------')
                outstr.extend(
                    ['%12.3f  %10.4g%+10.4gj' % (w, re, im)
                     for w, re, im in zip(self.omega,
                                          real(self.fresp[j, i, :]),
                                          imag(self.fresp[j, i, :]))])

        return '\n'.join(outstr)

    def __repr__(self):
        """Loadable string representation,

        limited for number of data points.
        """
        return "FrequencyResponseData({d}, {w}{smooth})".format(
            d=repr(self.fresp), w=repr(self.omega),
            smooth=(self.ifunc and ", smooth=True") or "")

    def __neg__(self):
        """Negate a transfer function."""

        return FRD(-self.fresp, self.omega)

    def __add__(self, other):
        """Add two LTI objects (parallel connection)."""

        if isinstance(other, FRD):
            # verify that the frequencies match
            if len(other.omega) != len(self.omega) or \
               (other.omega != self.omega).any():
                warn("Frequency points do not match; expect "
                     "truncation and interpolation.")

        # Convert the second argument to a frequency response function.
        # or re-base the frd to the current omega (if needed)
        other = _convert_to_frd(other, omega=self.omega)

        # Check that the input-output sizes are consistent.
        if self.ninputs != other.ninputs:
            raise ValueError(
                "The first summand has %i input(s), but the " \
                "second has %i." % (self.ninputs, other.ninputs))
        if self.noutputs != other.noutputs:
            raise ValueError(
                "The first summand has %i output(s), but the " \
                "second has %i." % (self.noutputs, other.noutputs))

        return FRD(self.fresp + other.fresp, other.omega)

    def __radd__(self, other):
        """Right add two LTI objects (parallel connection)."""

        return self + other

    def __sub__(self, other):
        """Subtract two LTI objects."""

        return self + (-other)

    def __rsub__(self, other):
        """Right subtract two LTI objects."""

        return other + (-self)

    def __mul__(self, other):
        """Multiply two LTI objects (serial connection)."""

        # Convert the second argument to a transfer function.
        if isinstance(other, (int, float, complex, np.number)):
            return FRD(self.fresp * other, self.omega,
                       smooth=(self.ifunc is not None))
        else:
            other = _convert_to_frd(other, omega=self.omega)

        # Check that the input-output sizes are consistent.
        if self.ninputs != other.noutputs:
            raise ValueError(
                "H = G1*G2: input-output size mismatch: "
                "G1 has %i input(s), G2 has %i output(s)." %
                (self.ninputs, other.noutputs))

        inputs = other.ninputs
        outputs = self.noutputs
        fresp = empty((outputs, inputs, len(self.omega)),
                      dtype=self.fresp.dtype)
        for i in range(len(self.omega)):
            fresp[:, :, i] = self.fresp[:, :, i] @ other.fresp[:, :, i]
        return FRD(fresp, self.omega,
                   smooth=(self.ifunc is not None) and
                          (other.ifunc is not None))

    def __rmul__(self, other):
        """Right Multiply two LTI objects (serial connection)."""

        # Convert the second argument to an frd function.
        if isinstance(other, (int, float, complex, np.number)):
            return FRD(self.fresp * other, self.omega,
                       smooth=(self.ifunc is not None))
        else:
            other = _convert_to_frd(other, omega=self.omega)

        # Check that the input-output sizes are consistent.
        if self.noutputs != other.ninputs:
            raise ValueError(
                "H = G1*G2: input-output size mismatch: "
                "G1 has %i input(s), G2 has %i output(s)." %
                (other.ninputs, self.noutputs))

        inputs = self.ninputs
        outputs = other.noutputs

        fresp = empty((outputs, inputs, len(self.omega)),
                      dtype=self.fresp.dtype)
        for i in range(len(self.omega)):
            fresp[:, :, i] = other.fresp[:, :, i] @ self.fresp[:, :, i]
        return FRD(fresp, self.omega,
                   smooth=(self.ifunc is not None) and
                          (other.ifunc is not None))

    # TODO: Division of MIMO transfer function objects is not written yet.
    def __truediv__(self, other):
        """Divide two LTI objects."""

        if isinstance(other, (int, float, complex, np.number)):
            return FRD(self.fresp * (1/other), self.omega,
                       smooth=(self.ifunc is not None))
        else:
            other = _convert_to_frd(other, omega=self.omega)

        if (self.ninputs > 1 or self.noutputs > 1 or
            other.ninputs > 1 or other.noutputs > 1):
            raise NotImplementedError(
                "FRD.__truediv__ is currently only implemented for SISO "
                "systems.")

        return FRD(self.fresp/other.fresp, self.omega,
                   smooth=(self.ifunc is not None) and
                          (other.ifunc is not None))

    # TODO: Division of MIMO transfer function objects is not written yet.
    def __rtruediv__(self, other):
        """Right divide two LTI objects."""
        if isinstance(other, (int, float, complex, np.number)):
            return FRD(other / self.fresp, self.omega,
                       smooth=(self.ifunc is not None))
        else:
            other = _convert_to_frd(other, omega=self.omega)

        if (self.ninputs > 1 or self.noutputs > 1 or
            other.ninputs > 1 or other.noutputs > 1):
            raise NotImplementedError(
                "FRD.__rtruediv__ is currently only implemented for "
                "SISO systems.")

        return other / self

    def __pow__(self, other):
        if not type(other) == int:
            raise ValueError("Exponent must be an integer")
        if other == 0:
            return FRD(ones(self.fresp.shape), self.omega,
                       smooth=(self.ifunc is not None))  # unity
        if other > 0:
            return self * (self**(other-1))
        if other < 0:
            return (FRD(ones(self.fresp.shape), self.omega) / self) * \
                (self**(other+1))

    # Define the `eval` function to evaluate an FRD at a given (real)
    # frequency.  Note that we choose to use `eval` instead of `evalfr` to
    # avoid confusion with :func:`evalfr`, which takes a complex number as its
    # argument.  Similarly, we don't use `__call__` to avoid confusion between
    # G(s) for a transfer function and G(omega) for an FRD object.
    # update Sawyer B. Fuller 2020.08.14: __call__ added to provide a uniform
    # interface to systems in general and the lti.frequency_response method
    def eval(self, omega, squeeze=None):
        """Evaluate a transfer function at angular frequency omega.

        Note that a "normal" FRD only returns values for which there is an
        entry in the omega vector. An interpolating FRD can return
        intermediate values.

        Parameters
        ----------
        omega : float or 1D array_like
            Frequencies in radians per second
        squeeze : bool, optional
            If squeeze=True, remove single-dimensional entries from the shape
            of the output even if the system is not SISO. If squeeze=False,
            keep all indices (output, input and, if omega is array_like,
            frequency) even if the system is SISO. The default value can be
            set using config.defaults['control.squeeze_frequency_response'].

        Returns
        -------
        fresp : complex ndarray
            The frequency response of the system.  If the system is SISO and
            squeeze is not True, the shape of the array matches the shape of
            omega.  If the system is not SISO or squeeze is False, the first
            two dimensions of the array are indices for the output and input
            and the remaining dimensions match omega.  If ``squeeze`` is True
            then single-dimensional axes are removed.

        """
        omega_array = np.array(omega, ndmin=1)  # array-like version of omega

        # Make sure that we are operating on a simple list
        if len(omega_array.shape) > 1:
            raise ValueError("input list must be 1D")

        # Make sure that frequencies are all real-valued
        if any(omega_array.imag > 0):
            raise ValueError("FRD.eval can only accept real-valued omega")

        if self.ifunc is None:
            elements = np.isin(self.omega, omega)  # binary array
            if sum(elements) < len(omega_array):
                raise ValueError(
                    "not all frequencies omega are in frequency list of FRD "
                    "system. Try an interpolating FRD for additional points.")
            else:
                out = self.fresp[:, :, elements]
        else:
            out = empty((self.noutputs, self.ninputs, len(omega_array)),
                        dtype=complex)
            for i in range(self.noutputs):
                for j in range(self.ninputs):
                    for k, w in enumerate(omega_array):
                        frraw = splev(w, self.ifunc[i, j], der=0)
                        out[i, j, k] = frraw[0] + 1.0j * frraw[1]

        return _process_frequency_response(self, omega, out, squeeze=squeeze)

    def __call__(self, s=None, squeeze=None, return_magphase=None):
        """Evaluate system's transfer function at complex frequencies.

        Returns the complex frequency response `sys(s)` of system `sys` with
        `m = sys.ninputs` number of inputs and `p = sys.noutputs` number of
        outputs.

        To evaluate at a frequency omega in radians per second, enter
        ``s = omega * 1j`` or use ``sys.eval(omega)``

        For a frequency response data object, the argument must be an
        imaginary number (since only the frequency response is defined).

        If ``s`` is not given, this function creates a copy of a frequency
        response data object with a different set of output settings.

        Parameters
        ----------
        s : complex scalar or 1D array_like
            Complex frequencies.  If not specified, return a copy of the
            frequency response data object with updated settings for output
            processing (``squeeze``, ``return_magphase``).

        squeeze : bool, optional
            If squeeze=True, remove single-dimensional entries from the shape
            of the output even if the system is not SISO. If squeeze=False,
            keep all indices (output, input and, if omega is array_like,
            frequency) even if the system is SISO. The default value can be
            set using config.defaults['control.squeeze_frequency_response'].

        return_magphase : bool, optional
            If True, then a frequency response data object will enumerate as a
            tuple of the form (mag, phase, omega) where where ``mag`` is the
            magnitude (absolute value, not dB or log10) of the system
            frequency response, ``phase`` is the wrapped phase in radians of
            the system frequency response, and ``omega`` is the (sorted)
            frequencies at which the response was evaluated.

        Returns
        -------
        fresp : complex ndarray
            The frequency response of the system.  If the system is SISO and
            squeeze is not True, the shape of the array matches the shape of
            omega.  If the system is not SISO or squeeze is False, the first
            two dimensions of the array are indices for the output and input
            and the remaining dimensions match omega.  If ``squeeze`` is True
            then single-dimensional axes are removed.

        Raises
        ------
        ValueError
            If `s` is not purely imaginary, because
            :class:`FrequencyResponseData` systems are only defined at
            imaginary values (corresponding to real frequencies).

        """
        if s is None:
            # Create a copy of the response with new keywords
            response = copy(self)

            # Update any keywords that we were passed
            response.squeeze = self.squeeze if squeeze is None else squeeze
            response.return_magphase = self.return_magphase \
                if return_magphase is None else return_magphase

            return response

        # Make sure that we are operating on a simple list
        if len(np.atleast_1d(s).shape) > 1:
            raise ValueError("input list must be 1D")

        if any(abs(np.atleast_1d(s).real) > 0):
            raise ValueError("__call__: FRD systems can only accept "
                             "purely imaginary frequencies")

        # need to preserve array or scalar status
        if hasattr(s, '__len__'):
            return self.eval(np.asarray(s).imag, squeeze=squeeze)
        else:
            return self.eval(complex(s).imag, squeeze=squeeze)

    # Implement iter to allow assigning to a tuple
    def __iter__(self):
        fresp = _process_frequency_response(
            self, self.omega, self.fresp, squeeze=self.squeeze)
        if self._return_singvals:
            # Legacy processing for singular values
            return iter((self.fresp[:, 0, :], self.omega))
        elif not self.return_magphase:
            return iter((self.omega, fresp))
        return iter((np.abs(fresp), np.angle(fresp), self.omega))

    # Implement (thin) getitem to allow access via legacy indexing
    def __getitem__(self, index):
        return list(self.__iter__())[index]

    # Implement (thin) len to emulate legacy testing interface
    def __len__(self):
        return 3 if self.return_magphase else 2

    def freqresp(self, omega):
        """(deprecated) Evaluate transfer function at complex frequencies.

        .. deprecated::0.9.0
            Method has been given the more pythonic name
            :meth:`FrequencyResponseData.frequency_response`. Or use
            :func:`freqresp` in the MATLAB compatibility module.

        """
        warn("FrequencyResponseData.freqresp(omega) will be removed in a "
             "future release of python-control; use "
             "FrequencyResponseData.frequency_response(omega), or "
             "freqresp(sys, omega) in the MATLAB compatibility module "
             "instead", FutureWarning)
        return self.frequency_response(omega)

    def feedback(self, other=1, sign=-1):
        """Feedback interconnection between two FRD objects."""

        other = _convert_to_frd(other, omega=self.omega)

        if (self.noutputs != other.ninputs or self.ninputs != other.noutputs):
            raise ValueError(
                "FRD.feedback, inputs/outputs mismatch")

        # TODO: handle omega re-mapping

        # reorder array axes in order to leverage numpy broadcasting
        myfresp = np.moveaxis(self.fresp, 2, 0)
        otherfresp = np.moveaxis(other.fresp, 2, 0)
        I_AB = eye(self.ninputs)[np.newaxis, :, :] + otherfresp @ myfresp
        resfresp = (myfresp @ linalg.inv(I_AB))
        fresp = np.moveaxis(resfresp, 0, 2)

        return FRD(fresp, other.omega, smooth=(self.ifunc is not None))

    # Plotting interface
    def plot(self, plot_type=None, *args, **kwargs):
        """Plot the frequency response using a Bode plot.

        Plot the frequency response using either a standard Bode plot
        (default) or using a singular values plot (by setting `plot_type`
        to 'svplot').  See :func:`~control.bode_plot` and
        :func:`~control.singular_values_plot` for more detailed
        descriptions.

        """
        from .freqplot import bode_plot, singular_values_plot
        from .nichols import nichols_plot

        if plot_type is None:
            plot_type = self.plot_type

        if plot_type == 'bode':
            return bode_plot(self, *args, **kwargs)
        elif plot_type == 'nichols':
            return nichols_plot(self, *args, **kwargs)
        elif plot_type == 'svplot':
            return singular_values_plot(self, *args, **kwargs)
        else:
            raise ValueError(f"unknown plot type '{plot_type}'")

    # Convert to pandas
    def to_pandas(self):
        """Convert response data to pandas data frame.

        Creates a pandas data frame for the value of the frequency
        response at each `omega`.  The frequency response values are
        labeled in the form "H_{<out>, <in>}" where "<out>" and "<in>"
        are replaced with the output and input labels for the system.

        """
        if not pandas_check():
            ImportError('pandas not installed')
        import pandas

        # Create a dict for setting up the data frame
        data = {'omega': self.omega}
        data.update(
            {'H_{%s, %s}' % (out, inp): self.fresp[i, j] \
             for i, out in enumerate(self.output_labels) \
             for j, inp in enumerate(self.input_labels)})

        return pandas.DataFrame(data)


#
# Allow FRD as an alias for the FrequencyResponseData class
#
# Note: This class was initially given the name "FRD", but this caused
# problems with documentation on MacOS platforms, since files were generated
# for control.frd and control.FRD, which are not differentiated on most MacOS
# filesystems, which are case insensitive.  Renaming the FRD class to be
# FrequenceResponseData and then assigning FRD to point to the same object
# fixes this problem.
#
FRD = FrequencyResponseData


def _convert_to_frd(sys, omega, inputs=1, outputs=1):
    """Convert a system to frequency response data form (if needed).

    If sys is already an frd, and its frequency range matches or
    overlaps the range given in omega then it is returned.  If sys is
    another LTI object or a transfer function, then it is converted to
    a frequency response data at the specified omega. If sys is a
    scalar, then the number of inputs and outputs can be specified
    manually, as in:

    >>> import numpy as np
    >>> from control.frdata import _convert_to_frd

    >>> omega = np.logspace(-1, 1)
    >>> frd = _convert_to_frd(3., omega) # Assumes inputs = outputs = 1
    >>> frd.ninputs, frd.noutputs
    (1, 1)

    >>> frd = _convert_to_frd(1., omega, inputs=3, outputs=2)
    >>> frd.ninputs, frd.noutputs
    (3, 2)

    In the latter example, sys's matrix transfer function is [[1., 1., 1.]
                                                              [1., 1., 1.]].

    """

    if isinstance(sys, FRD):
        omega.sort()
        if len(omega) == len(sys.omega) and \
           (abs(omega - sys.omega) < FRD._epsw).all():
            # frequencies match, and system was already frd; simply use
            return sys

        raise NotImplementedError(
            "Frequency ranges of FRD do not match, conversion not implemented")

    elif isinstance(sys, LTI):
        omega = np.sort(omega)
        if sys.isctime():
            fresp = sys(1j * omega)
        else:
            fresp = sys(np.exp(1j * omega * sys.dt))
        if len(fresp.shape) == 1:
            fresp = fresp[np.newaxis, np.newaxis, :]
        return FRD(fresp, omega, smooth=True)

    elif isinstance(sys, (int, float, complex, np.number)):
        fresp = ones((outputs, inputs, len(omega)), dtype=float)*sys
        return FRD(fresp, omega, smooth=True)

    # try converting constant matrices
    try:
        sys = array(sys)
        outputs, inputs = sys.shape
        fresp = empty((outputs, inputs, len(omega)), dtype=float)
        for i in range(outputs):
            for j in range(inputs):
                fresp[i, j, :] = sys[i, j]
        return FRD(fresp, omega, smooth=True)
    except Exception:
        pass

    raise TypeError('''Can't convert given type "%s" to FRD system.''' %
                    sys.__class__)


def frd(*args, **kwargs):
    """frd(response, omega[, dt])

    Construct a frequency response data (FRD) model.

    A frequency response data model stores the (measured) frequency response
    of a system.  This factory function can be called in different ways:

    ``frd(response, omega)``
        Create an frd model with the given response data, in the form of
        complex response vector, at matching frequencies ``omega`` [in rad/s].

    ``frd(sys, omega)``
        Convert an LTI system into an frd model with data at frequencies
        ``omega``.

    Parameters
    ----------
    response : array_like or LTI system
        Complex vector with the system response or an LTI system that can
        be used to copmute the frequency response at a list of frequencies.
    omega : array_like
        Vector of frequencies at which the response is evaluated.
    dt : float, True, or None
        System timebase.
    smooth : bool, optional
        If ``True``, create an interpolation function that allows the
        frequency response to be computed at any frequency within the range
        of frequencies give in ``omega``.  If ``False`` (default),
        frequency response can only be obtained at the frequencies
        specified in ``omega``.

    Returns
    -------
    sys : :class:`FrequencyResponseData`
        New frequency response data system.

    Other Parameters
    ----------------
    inputs, outputs : str, or list of str, optional
        List of strings that name the individual signals of the transformed
        system.  If not given, the inputs and outputs are the same as the
        original system.
    name : string, optional
        System name. If unspecified, a generic name <sys[id]> is generated
        with a unique integer id.

    See Also
    --------
    FrequencyResponseData, frequency_response, ss, tf

    Examples
    --------
    >>> # Create from measurements
    >>> response = [1.0, 1.0, 0.5]
    >>> omega = [1, 10, 100]
    >>> F = ct.frd(response, omega)

    >>> G = ct.tf([1], [1, 1])
    >>> omega = [1, 10, 100]
    >>> F = ct.frd(G, omega)

    """
    return FrequencyResponseData(*args, **kwargs)
