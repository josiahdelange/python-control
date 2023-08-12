# pzmap.py - computations involving poles and zeros
#
# Original author: Richard M. Murray
# Date: 7 Sep 2009
#
# This file contains functions that compute poles, zeros and related
# quantities for a linear system.
#

import numpy as np
from numpy import real, imag, linspace, exp, cos, sin, sqrt
import matplotlib.pyplot as plt
from math import pi
import itertools
import warnings

from .lti import LTI
from .iosys import isdtime, isctime
from .grid import sgrid, zgrid, nogrid
from .statesp import StateSpace
from .xferfcn import TransferFunction
from .freqplot import _freqplot_defaults, _get_line_labels
from . import config

__all__ = ['pole_zero_map', 'root_locus_map', 'pole_zero_plot', 'pzmap']


# Define default parameter values for this module
_pzmap_defaults = {
    'pzmap.grid': False,       # Plot omega-damping grid
    'pzmap.marker_size': 6,    # Size of the markers
    'pzmap.marker_width': 1.5, # Width of the markers
}


# Classes for keeping track of pzmap plots
class RootLocusList(list):
    def plot(self, *args, **kwargs):
        return pole_zero_plot(self, *args, **kwargs)


class RootLocusData:
    def __init__(
            self, poles, zeros, gains=None, loci=None, xlim=None, ylim=None,
            dt=None, sysname=None):
        self.poles = poles
        self.zeros = zeros
        self.gains = gains
        self.loci = loci
        self.xlim = xlim
        self.ylim = ylim
        self.dt = dt
        self.sysname = sysname

    # Implement functions to allow legacy assignment to tuple
    def __iter__(self):
        return iter((self.poles, self.zeros))

    def plot(self, *args, **kwargs):
        return pole_zero_plot(self, *args, **kwargs)


# Pole/zero map
def pole_zero_map(sysdata):
    # Convert the first argument to a list
    syslist = sysdata if isinstance(sysdata, (list, tuple)) else [sysdata]

    responses = []
    for idx, sys in enumerate(syslist):
        responses.append(
            RootLocusData(
                sys.poles(), sys.zeros(), dt=sys.dt, sysname=sys.name))

    if isinstance(sysdata, (list, tuple)):
        return RootLocusList(responses)
    else:
        return responses[0]


# Root locus map
def root_locus_map(sysdata, gains=None, xlim=None, ylim=None):
    # Convert the first argument to a list
    syslist = sysdata if isinstance(sysdata, (list, tuple)) else [sysdata]

    responses = []
    for idx, sys in enumerate(syslist):
        from .rlocus import _systopoly1d, _default_gains
        from .rlocus import _RLFindRoots, _RLSortRoots

        if not sys.issiso():
            raise ControlMIMONotImplemented(
                "sys must be single-input single-output (SISO)")

        # Convert numerator and denominator to polynomials if they aren't
        nump, denp = _systopoly1d(sys[0, 0])

        if xlim is None and sys.isdtime(strict=True):
            xlim = (-1.2, 1.2)
        if ylim is None and sys.isdtime(strict=True):
            xlim = (-1.3, 1.3)

        if gains is None:
            kvect, root_array, xlim, ylim = _default_gains(
                nump, denp, xlim, ylim)
        else:
            kvect = np.atleast_1d(gains)
            root_array = _RLFindRoots(nump, denp, kvect)
            root_array = _RLSortRoots(root_array)

        responses.append(RootLocusData(
            sys.poles(), sys.zeros(), kvect, root_array,
            dt=sys.dt, sysname=sys.name, xlim=xlim, ylim=ylim))

    if isinstance(sysdata, (list, tuple)):
        return RootLocusList(responses)
    else:
        return responses[0]


# TODO: Implement more elegant cross-style axes. See:
#    https://matplotlib.org/2.0.2/examples/axes_grid/demo_axisline_style.html
#    https://matplotlib.org/2.0.2/examples/axes_grid/demo_curvelinear_grid.html
def pole_zero_plot(
        data, plot=None, grid=None, title=None, marker_color=None,
        marker_size=None, marker_width=None, legend_loc='upper right',
        xlim=None, ylim=None, **kwargs):
    """Plot a pole/zero map for a linear system.

    Parameters
    ----------
    sysdata: List of RootLocusData objects or LTI systems
        List of pole/zero response data objects generated by pzmap_response
        or rootlocus_response() that are to be plotted.  If a list of systems
        is given, the poles and zeros of those systems will be plotted.
    grid: boolean (default = False)
        If True plot omega-damping grid.
    plot: bool, optional
        (legacy) If ``True`` a graph is generated with Matplotlib,
        otherwise the poles and zeros are only computed and returned.
        If this argument is present, the legacy value of poles and
        zero is returned.

    Returns
    -------
    lines : List of Line2D
        Array of Line2D objects for each set of markers in the plot. The
        shape of the array is given by (nsys, 2) where nsys is the number
        of systems or Nyquist responses passed to the function.  The second
        index specifies the pzmap object type:

        * lines[idx, 0]: poles
        * lines[idx, 1]: zeros

    poles, zeros: list of arrays
        (legacy) If the `plot` keyword is given, the system poles and zeros
        are returned.

    Notes (TODO: update)
    -----
    The pzmap function calls matplotlib.pyplot.axis('equal'), which means
    that trying to reset the axis limits may not behave as expected.  To
    change the axis limits, use matplotlib.pyplot.gca().axis('auto') and
    then set the axis limits to the desired values.

    """
    # Get parameter values
    grid = config._get_param('pzmap', 'grid', grid, False)
    marker_size = config._get_param('pzmap', 'marker_size', marker_size, 6)
    marker_width = config._get_param('pzmap', 'marker_width', marker_width, 1.5)
    xlim_user, ylim_user = xlim, ylim
    freqplot_rcParams = config._get_param(
        'freqplot', 'rcParams', kwargs, _freqplot_defaults,
        pop=True, last=True)

    # If argument was a singleton, turn it into a tuple
    if not isinstance(data, (list, tuple)):
        data = [data]

    # If we are passed a list of systems, compute response first
    if all([isinstance(
            sys, (StateSpace, TransferFunction)) for sys in data]):
        # Get the response, popping off keywords used there
        pzmap_responses = pole_zero_map(data)
    elif all([isinstance(d, RootLocusData) for d in data]):
        pzmap_responses = data
    else:
        raise TypeError("unknown system data type")

    # Legacy return value processing
    if plot is not None:
        warnings.warn(
            "`pole_zero_plot` return values of poles, zeros is deprecated; "
            "use pole_zero_map()", DeprecationWarning)

        # Extract out the values that we will eventually return
        poles = [response.poles for response in pzmap_responses]
        zeros = [response.zeros for response in pzmap_responses]

    if plot is False:
        if len(data) == 1:
            return poles[0], zeros[0]
        else:
            return poles, zeros

    # Initialize the figure
    # TODO: turn into standard utility function
    fig = plt.gcf()
    axs = fig.get_axes()
    if len(axs) > 1:
        # Need to generate a new figure
        fig, axs = plt.figure(), []

    with plt.rc_context(freqplot_rcParams):
        if grid:
            plt.clf()
            if all([response.dt in [0, None] for response in data]):
                ax, fig = sgrid()
            elif all([response.dt > 0 for response in data]):
                ax, fig = zgrid()
            else:
                ValueError(
                    "incompatible time responses; don't know how to grid")
        elif len(axs) == 0:
            ax, fig = nogrid()
        else:
            # Use the existing axes
            ax = axs[0]

    # Handle color cycle manually as all singular values
    # of the same systems are expected to be of the same color
    color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
    color_offset = 0
    if len(ax.lines) > 0:
        last_color = ax.lines[-1].get_color()
        if last_color in color_cycle:
            color_offset = color_cycle.index(last_color) + 1

    # Create a list of lines for the output
    out = np.empty((len(pzmap_responses), 3), dtype=object)
    for i, j in itertools.product(range(out.shape[0]), range(out.shape[1])):
        out[i, j] = []          # unique list in each element

    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    for idx, response in enumerate(pzmap_responses):
        poles = response.poles
        zeros = response.zeros

        # Get the color to use for this system
        if marker_color is None:
            color = color_cycle[(color_offset + idx) % len(color_cycle)]
        else:
            color = maker_color

        # Plot the locations of the poles and zeros
        if len(poles) > 0:
            label = response.sysname if response.loci is None else None
            out[idx, 0] = ax.plot(
                real(poles), imag(poles), marker='x', linestyle='',
                markeredgecolor=color, markerfacecolor=color,
                markersize=marker_size, markeredgewidth=marker_width,
                label=label)
        if len(zeros) > 0:
            out[idx, 1] = ax.plot(
                real(zeros), imag(zeros), marker='o', linestyle='',
                markeredgecolor=color, markerfacecolor='none',
                markersize=marker_size, markeredgewidth=marker_width)

        # Plot the loci, if present
        if response.loci is not None:
            for locus in response.loci.transpose():
                out[idx, 2] += ax.plot(
                    real(locus), imag(locus), color=color,
                    label=response.sysname)

        # Compute the axis limits to use
        if response.xlim is not None:
            xlim = (min(xlim[0], response.xlim[0]),
                    max(xlim[1], response.xlim[1]))
        if response.ylim is not None:
            ylim = (min(ylim[0], response.ylim[0]),
                    max(ylim[1], response.ylim[1]))

    # Set up the limits for the plot
    ax.set_xlim(xlim if xlim_user is None else xlim_user)
    ax.set_ylim(ylim if ylim_user is None else ylim_user)

    # List of systems that are included in this plot
    lines, labels = _get_line_labels(ax)

    # Add legend if there is more than one system plotted
    if len(labels) > 1 and legend_loc is not False:
        if response.loci is None:
            # Use "x o" for the system label, via matplotlib tuple handler
            from matplotlib.lines import Line2D
            from matplotlib.legend_handler import HandlerTuple

            line_tuples = []
            for pole_line in lines:
                zero_line = Line2D(
                    [0], [0], marker='o', linestyle='',
                    markeredgecolor=pole_line.get_markerfacecolor(),
                    markerfacecolor='none', markersize=marker_size,
                    markeredgewidth=marker_width)
            handle = (pole_line, zero_line)
            line_tuples.append(handle)

            with plt.rc_context(freqplot_rcParams):
                ax.legend(
                    line_tuples, labels, loc=legend_loc,
                    handler_map={tuple: HandlerTuple(ndivide=None)})
        else:
            # Regular legend, with lines
            with plt.rc_context(freqplot_rcParams):
                ax.legend(lines, labels, loc=legend_loc)

    # Add the title
    if title is None:
        title = "Pole/zero plot for " + ", ".join(labels)
    with plt.rc_context(freqplot_rcParams):
        fig.suptitle(title)

    # Legacy processing: return locations of poles and zeros as a tuple
    if plot is True:
        if len(data) == 1:
            return poles, zeros
        else:
            TypeError("system lists not supported with legacy return values")

    return out


pzmap = pole_zero_plot
