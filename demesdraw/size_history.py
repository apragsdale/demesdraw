import demes
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from demesdraw import utils


def size_history(
    graph: demes.Graph,
    ax: matplotlib.axes.Axes = None,
    inf_ratio: float = 0.1,
    inf_label: bool = False,
    invert_x: bool = False,
    num_exp_points: int = 100,
    annotate_epochs: bool = False,
    cmap: matplotlib.colors.Colormap = None,
    log_x: bool = False,
    log_y: bool = False,
    title: str = None,
):
    """
    Plot population size as a function of time for each deme in the graph.

    :param demes.Graph graph: The demes graph to plot.
    :param matplotlib.axes.Axes ax: The matplotlib axes onto which the figure
        will be drawn. If None, an empty axes will be created for the figure.
    :param float inf_ratio: The proportion of the horizontal axis that will be
        used for the time interval which stretches towards infinity.
    :param bool inf_label: Write "inf" by the arrow that points towards infinity.
    :param bool invert_x: If true, the horizontal axis will have infinity
        on the left and zero on the right, and the vertical axis will be drawn
        on the right.
    :param int num_exp_points: The number of points used to approximate
        size changes in each epoch with exponential size_function.
    :param bool annotate_epochs: Annotate the figure with epoch indices
        over the relevant parts of the lines. This is mostly useful as a
        pedagogical tool.
    :param matplotlib.colors.Colormap cmap: A matplotlib colour map to be used
        for the different demes. Get one with :func:`matplotlib.cm.get_cmap()`.
        If None, tab10 or tab20 will be used, depending on the number of demes.
    :param bool log_x: Use a log-10 scale for the horizontal axis.
    :param bool log_y: Use a log-10 scale for the vertical axis.
    :param str title: The title of the figure.

    :return: The matplotlib axes onto which the figure was drawn.
    :rtype: matplotlib.axes.Axes
    """
    if ax is None:
        fig_w, fig_h = plt.figaspect(9.0 / 16.0)
        _, ax = plt.subplots(figsize=(fig_w, fig_h))

    if invert_x:
        arrowhead = "<k"
    else:
        arrowhead = ">k"

    if cmap is None:
        if len(graph.demes) <= 10:
            cmap = matplotlib.cm.get_cmap("tab10")
        elif len(graph.demes) <= 20:
            cmap = matplotlib.cm.get_cmap("tab20")
        else:
            raise ValueError(
                "Graph has more than 20 demes, so cmap must be specified. Good luck!"
            )

    inf_start_time = utils.inf_start_time(graph, inf_ratio, log_x)

    linestyles = ["solid"]  # , "dashed", "dashdot"]
    linewidths = [2, 4, 8, 1]
    legend_handles = []
    # Top of the z order stacking.
    z_top = 1 + len(graph.demes) + max(linewidths)

    for j, deme in enumerate(graph.demes):
        colour = cmap(j)
        linestyle = linestyles[j % len(linestyles)]
        linewidth = linewidths[j % len(linewidths)]
        plot_kwargs = dict(
            color=colour,
            linestyle=linestyle,
            linewidth=linewidth,
            label=deme.id,
            alpha=0.7,
            zorder=z_top - linewidth,
            solid_capstyle="butt",
        )
        discontinuity_kwargs = dict(
            color=colour,
            linestyle=":",
            linewidth=linewidth,
            alpha=0.7,
            zorder=z_top - linewidth,
            solid_capstyle="butt",
        )
        legend_handles.append(matplotlib.lines.Line2D([], [], **plot_kwargs))

        for k, epoch in enumerate(deme.epochs):
            start_time = epoch.start_time
            if np.isinf(start_time):
                start_time = inf_start_time
            end_time = epoch.end_time
            if end_time == 0 and log_x:
                end_time = 1

            if epoch.size_function == "constant":
                x = np.array([start_time, end_time])
                y = np.array([epoch.start_size, epoch.end_size])
            elif epoch.size_function == "exponential":
                x = np.linspace(start_time, end_time, num=num_exp_points)
                dt = np.linspace(0, 1, num=num_exp_points)
                r = np.log(epoch.end_size / epoch.start_size)
                y = epoch.start_size * np.exp(r * dt)
            else:
                raise ValueError(
                    f"Don't know how to plot epoch {k} with "
                    f'"{epoch.size_function}" size_function.'
                )

            ax.plot(x, y, **plot_kwargs)
            if k > 0 and deme.epochs[k - 1].end_size != epoch.start_size:
                # Indicate population size discontinuity.
                ax.plot(
                    [deme.epochs[k - 1].end_time, epoch.start_time],
                    [deme.epochs[k - 1].end_size, epoch.start_size],
                    **discontinuity_kwargs,
                )

            if annotate_epochs:
                if log_x:
                    text_x = np.exp((np.log(start_time) + np.log(end_time)) / 2)
                else:
                    text_x = (start_time + end_time) / 2
                if log_y:
                    text_y = np.exp(
                        (np.log(1 + epoch.start_size) + np.log(1 + epoch.end_size)) / 2
                    )
                else:
                    text_y = (epoch.start_size + epoch.end_size) / 2
                ax.annotate(
                    f"epoch {k}",
                    (text_x, text_y),
                    ha="center",
                    va="bottom",
                    xytext=(0, 4 + linewidth / 2),  # vertical offset
                    textcoords="offset points",
                    # Give the text some contrast with its background.
                    bbox=dict(
                        boxstyle="round", fc="white", ec="none", alpha=0.6, pad=0
                    ),
                    # This is only really a useful feature with 1 deme,
                    # but at least try to do something reasonable for more demes.
                    color="black" if len(graph.demes) == 1 else colour,
                )

        if np.isinf(deme.start_time):
            # Plot an arrow at the end of the line, to indicate this
            # line extends towards infinity.
            ax.plot(
                inf_start_time,
                deme.epochs[0].start_size,
                arrowhead,
                color=colour,
                clip_on=False,
                zorder=z_top,
            )
            if inf_label:
                ax.annotate(
                    "inf",
                    (inf_start_time, deme.epochs[0].start_size),
                    xytext=(0, -6),  # vertical offset
                    textcoords="offset points",
                    clip_on=False,
                    ha="center",
                    va="top",
                )

        # Indicate population size discontinuities from ancestor demes.
        for ancestor_id in deme.ancestors:
            anc = graph[ancestor_id]
            anc_N = utils.size_of_deme_at_time(anc, deme.start_time)
            deme_N = deme.epochs[0].start_size
            if anc_N != deme_N:
                ax.plot(
                    [deme.start_time, deme.start_time],
                    [anc_N, deme_N],
                    **discontinuity_kwargs,
                )

    if len(graph.demes) > 1:
        leg = ax.legend(handles=legend_handles, ncol=len(graph.demes) // 2)
        leg.set_zorder(z_top)

    if title is not None:
        ax.set_title(title)

    # Arrange the axes spines, ticks and labels.

    ax.set_xlim(1 if log_x else 0, inf_start_time)
    # ax.set_ylim(1 if log_y else 0, None)

    ax.spines["top"].set_visible(False)
    if invert_x:
        ax.spines["left"].set_visible(False)
        ax.invert_xaxis()
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
    else:
        ax.spines["right"].set_visible(False)

    ax.set_xlabel(f"time ago ({graph.time_units})")
    # ax.set_ylabel("N", rotation=0, ha="left" if invert_x else "right")
    ax.set_ylabel("deme\nsize", rotation=0, labelpad=20)

    if log_x:
        ax.set_xscale("log", base=10)
    if log_y:
        ax.set_yscale("log", base=10)

    ax.figure.tight_layout()
    return ax


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Plot N(t) for all demes in a Demes graph."
    )
    parser.add_argument(
        "--inf-ratio",
        type=float,
        default=0.1,
        help=(
            "The proportion of the horizontal axis that will be "
            "used for the time interval which stretches towards infinity "
            "[default=%(default)s]."
        ),
    )
    parser.add_argument(
        "--invert-x",
        action="store_true",
        help=(
            "Invert the horizontal axis. "
            "I.e. draw the past on the left, the present on the right. "
            "The vertical axis ticks/labels will also be drawn on the right. "
        ),
    )
    parser.add_argument(
        "--log-x", action="store_true", help="Use a log scale for the horizontal axis."
    )
    parser.add_argument(
        "--log-y", action="store_true", help="Use a log scale for the vertical axis."
    )
    parser.add_argument(
        "--annotate-epochs",
        action="store_true",
        help=("Label each deme's epochs. " "Not recommended for more than one deme."),
    )
    parser.add_argument(
        "yaml_filename",
        metavar="demes.yaml",
        help="The Demes graph to plot.",
    )
    parser.add_argument(
        "plot_filename",
        metavar="figure.pdf",
        help=(
            "Output filename for the figure. "
            "Any file extension supported by matplotlib may be provided "
            "(pdf, eps, png, svg)."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    graph = demes.load(args.yaml_filename)
    ax = size_history(
        graph,
        inf_ratio=args.inf_ratio,
        invert_x=args.invert_x,
        log_x=args.log_x,
        log_y=args.log_y,
        annotate_epochs=args.annotate_epochs,
    )
    ax.figure.savefig(args.plot_filename)
