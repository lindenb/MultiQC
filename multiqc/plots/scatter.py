#!/usr/bin/env python

""" MultiQC functions to plot a scatter plot """

import logging
import random

from multiqc.utils import config, report

logger = logging.getLogger(__name__)

letters = "abcdefghijklmnopqrstuvwxyz"

# Load the template so that we can access its configuration
# Do this lazily to mitigate import-spaghetti when running unit tests
_template_mod = None


def get_template_mod():
    global _template_mod
    if not _template_mod:
        _template_mod = config.avail_templates[config.template].load()
    return _template_mod


def plot(data, pconfig=None):
    """Plot a scatter plot with X,Y data.
    :param data: 2D dict, first keys as sample names, then x:y data pairs
    :param pconfig: optional dict with config key:value pairs. See CONTRIBUTING.md
    :return: HTML and JS, ready to be inserted into the page
    """
    if pconfig is None:
        pconfig = {}

    # Allow user to overwrite any given config for this plot
    if "id" in pconfig and pconfig["id"] and pconfig["id"] in config.custom_plot_config:
        for point, v in config.custom_plot_config[pconfig["id"]].items():
            pconfig[point] = v

    # Given one dataset - turn it into a list
    if not isinstance(data, list):
        data = [data]

    # Generate the data dict structure expected by HighCharts series
    plotdata = list()
    for data_index, ds in enumerate(data):
        d = list()
        for s_name in ds:
            # Ensure any overwriting conditionals from data_labels (e.g. ymax) are taken in consideration
            series_config = pconfig.copy()
            if "data_labels" in pconfig and isinstance(
                pconfig["data_labels"][data_index], dict
            ):  # if not a dict: only dataset name is provided
                series_config.update(pconfig["data_labels"][data_index])

            if not isinstance(ds[s_name], list):
                ds[s_name] = [ds[s_name]]
            for point in ds[s_name]:
                if point["x"] is not None:
                    if "xmax" in series_config and float(point["x"]) > float(series_config["xmax"]):
                        continue
                    if "xmin" in series_config and float(point["x"]) < float(series_config["xmin"]):
                        continue
                if point["y"] is not None:
                    if "ymax" in series_config and float(point["y"]) > float(series_config["ymax"]):
                        continue
                    if "ymin" in series_config and float(point["y"]) < float(series_config["ymin"]):
                        continue
                if "name" in point:
                    point["name"] = f'{s_name}: {point["name"]}'
                else:
                    point["name"] = s_name

                for k in ["color", "opacity", "marker_size", "marker_line_width"]:
                    if k not in point and k in series_config:
                        v = series_config[k]
                        if isinstance(v, dict) and s_name in v:
                            point[k] = v[s_name]
                        else:
                            point[k] = v
                d.append(point)
        plotdata.append(d)

    if pconfig.get("square"):
        # Making sure HighCharts doesn't get creative in adding different paddings
        pconfig["endOnTick"] = False
        if "ymax" not in pconfig and "xmax" not in pconfig:
            # Find the max value
            max_val = 0
            for d in plotdata:
                for s in d:
                    max_val = max(max_val, s["x"], s["y"])
            max_val = 1.02 * max_val  # add 2% padding
            pconfig["xmax"] = pconfig.get("xmax", max_val)
            pconfig["ymax"] = pconfig.get("ymax", max_val)

    # Add on annotation data series
    try:
        if pconfig.get("extra_series"):
            extra_series = pconfig["extra_series"]
            if isinstance(pconfig["extra_series"], dict):
                extra_series = [[pconfig["extra_series"]]]
            elif isinstance(pconfig["extra_series"], list) and isinstance(pconfig["extra_series"][0], dict):
                extra_series = [pconfig["extra_series"]]
            for i, es in enumerate(extra_series):
                for s in es:
                    plotdata[i].append(s)
    except Exception:
        pass

    # Make a plot
    mod = get_template_mod()
    if "scatter" in mod.__dict__ and callable(mod.scatter):
        try:
            return mod.scatter(plotdata, pconfig)
        except:  # noqa: E722
            if config.strict:
                # Crash quickly in the strict mode. This can be helpful for interactive
                # debugging of modules
                raise
    return highcharts_scatter_plot(plotdata, pconfig)


def highcharts_scatter_plot(plotdata, pconfig=None):
    """
    Build the HTML needed for a HighCharts scatter plot. Should be
    called by scatter.plot(), which properly formats input data.
    """
    if pconfig is None:
        pconfig = {}

    # Get the plot ID
    if pconfig.get("id") is None:
        pconfig["id"] = "mqc_hcplot_" + "".join(random.sample(letters, 10))

    # Sanitise plot ID and check for duplicates
    pconfig["id"] = report.save_htmlid(pconfig["id"])

    # Build the HTML for the page
    html = '<div class="mqc_hcplot_plotgroup">'

    # Buttons to cycle through different datasets
    if len(plotdata) > 1:
        html += '<div class="btn-group hc_switch_group">\n'
        for k, p in enumerate(plotdata):
            active = "active" if k == 0 else ""
            dls = [dl if isinstance(dl, dict) else {"name": dl} for dl in pconfig.get("data_labels", [])]
            try:
                name = dls[k]["name"]
            except Exception:
                name = k + 1
            try:
                ylab = f"data-ylab=\"{dls[k]['ylab']}\""
            except Exception:
                ylab = f'data-ylab="{name}"' if name != k + 1 else ""
            try:
                ymax = f"data-ymax=\"{dls[k]['ymax']}\""
            except Exception:
                ymax = ""
            try:
                xlab = f"data-xlab=\"{dls[k]['xlab']}\""
            except Exception:
                xlab = f'data-xlab="{name}"' if name != k + 1 else ""
            html += '<button class="btn btn-default btn-sm {a}" data-action="set_data" {y} {ym} {xl} data-newdata="{k}" data-target="{id}">{n}</button>\n'.format(
                a=active, id=pconfig["id"], n=name, y=ylab, ym=ymax, xl=xlab, k=k
            )
        html += "</div>\n\n"

    # The plot div
    html += '<div class="hc-plot-wrapper"{height}><div id="{id}" class="hc-plot not_rendered hc-scatter-plot"><small>loading..</small></div></div></div> \n'.format(
        id=pconfig["id"],
        height=f' style="height:{pconfig["height"]}px"' if "height" in pconfig else "",
    )

    report.num_hc_plots += 1

    # Reverse order of dots in plotdata as the z-order is reversed in Highcharts compared to Plotly
    for d in plotdata:
        d.reverse()

    report.plot_data[pconfig["id"]] = {"plot_type": "scatter", "datasets": plotdata, "config": pconfig}

    return html
