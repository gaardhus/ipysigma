#!/usr/bin/env python
# coding: utf-8
# =============================================================================
# Sigma Jupyter Widget
# =============================================================================
#
#
from collections.abc import Iterable, Mapping
from ipywidgets import DOMWidget, HTML
from traitlets import Unicode, Dict, Int, Bool
import networkx as nx
from ._frontend import module_name, module_version

# =============================================================================
# Constants
# =============================================================================
MULTI_GRAPHS = (nx.MultiGraph, nx.MultiDiGraph)
DIRECTED_GRAPHS = (nx.DiGraph, nx.MultiDiGraph)
DEFAULT_NODE_SIZE_RANGE = (2, 12)
DEFAULT_EDGE_SIZE_RANGE = (0.5, 10)
SUPPORTED_NODE_TYPES = (int, str, float)


# =============================================================================
# Helpers
# =============================================================================
def pretty_print_int(v):
    return "{:,}".format(int(v))


def extract_rgba_from_viz(viz_color):
    if "a" in viz_color:
        return "rgba(%s, %s, %s, %s)" % (
            viz_color["r"],
            viz_color["g"],
            viz_color["b"],
            viz_color["a"],
        )

    return "rgba(%s, %s, %s)" % (
        viz_color["r"],
        viz_color["g"],
        viz_color["b"],
    )


def resolve_variable_kwarg(items, variable, name, target, allow_arbitrary_data=True):
    if isinstance(target, str):
        variable["attribute"] = target

    elif isinstance(target, (Iterable, Mapping)):
        if not allow_arbitrary_data:
            raise TypeError("%s should be a string" % name)

        mapping = dict(target)
        target = "$$%s" % name

        for node in items:
            v = mapping.get(node["key"])

            if v is None:
                continue

            node["attributes"][target] = v

        variable["attribute"] = target

    else:
        raise TypeError("%s should be a string, an iterable or a mapping" % name)


def process_node_gexf_viz(attr):
    if "viz" not in attr:
        return

    viz = attr["viz"]

    # Size
    if "size" in viz and "size" not in attr:
        attr["size"] = viz["size"]

    # Position
    if "position" in viz and "x" not in attr and "y" not in attr:
        pos = viz["position"]

        if "x" in pos:
            attr["x"] = pos["x"]

        if "y" in pos:
            attr["y"] = pos["y"]

    # Color
    if "color" in viz and "color" not in attr:
        attr["color"] = extract_rgba_from_viz(viz["color"])

    del attr["viz"]


def process_edge_gexf_viz(attr):
    if "viz" not in attr:
        return

    viz = attr["viz"]

    # Thickness
    if "thickness" in viz and "size" not in attr:
        attr["size"] = viz["thickness"]

    # Color
    if "color" in viz and "color" not in attr:
        attr["color"] = extract_rgba_from_viz(viz["color"])

    del attr["viz"]


# =============================================================================
# Widget definition
# =============================================================================
class Sigma(DOMWidget):
    """
    Jupyter widget displaying an interactive interface that can be used to
    explore the given networkx graph using sigma.js.

    Args:
        graph (nx.Graph or nx.DiGraph or nx.MultiGraph or nx.MultiDiGraph):
            networkx graph to explore.
        height (int, optional): height of the widget in pixels. Cannot be less
            than 250px. Defaults to 500.
        start_layout (bool, optional): whether to automatically start the
            provided ForceAtlas2 layout when the widget is displayed.
            Defaults to False.
        node_color (str, optional): name of the node attribute that should
            be interpreted as a category to be used for node color. Note that
            a suitable color palette will be automatically generated for you.
            Defaults to None, i.e. will read the "color" attribute of nodes
            directly or use a grey color if none is to be found.
        node_size (str, optional): name of the node attribute that should be
            used for node size. Note the provided size is scaled using
            the range provided by the `node_size_range` kwarg.
            Defaults to "size".
        node_size_range ((number, number), optional): range for node size
            interpolation. Defaults to (2, 12).
        node_label (str, optional): name of the node attribute that will be used
            as node label. Defaults to "label".
        edge_color (str, optional): name of the edge attribute that should
            be interpreted as a category to be used for edge color. Note that
            a suitable color palette will be automatically generated for you.
            Defaults to None, i.e. will read the "color" attribute of edges
            directly or use a light grey color if none is to be found.
        edge_size (str, optional): name of the edge attribute that should be
            used for edge size. Note the provided size is scaled using
            the range provided by the `edge_size_range` kwarg.
            Defaults to "size".
        edge_size_range ((number, number), optional): range for edge size
            interpolation. Defaults to (0.5, 10).
        edge_label (str, optional): name of the edge attribute that will be used
            as edge label. Defaults to None, i.e. no label.
        clickable_edges (bool, optional): whether to enable edge events so you can
            click on them to get information. This can be costly on large graphs.
            Defaults to False.
        process_gexf_viz (bool, optional): whether to process "viz" data typically
            found in gexf files so they can be displayed correctly.
            Defaults to True.
    """

    _model_name = Unicode("SigmaModel").tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode("SigmaView").tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)

    singleton_lock = Bool(False).tag(sync=True)
    data = Dict({"nodes": [], "edges": []}).tag(sync=True)
    height = Int(500).tag(sync=True)
    start_layout = Bool(False).tag(sync=True)
    clickable_edges = Bool(False).tag(sync=True)
    snapshot = Unicode(allow_none=True).tag(sync=True)
    layout = Dict(allow_none=True).tag(sync=True)
    visual_variables = Dict(
        {
            "node_label": {"type": "raw", "attribute": "label"},
            "node_color": {"type": "raw", "attribute": "color"},
            "node_size": {
                "type": "continuous",
                "attribute": "size",
                "range": DEFAULT_NODE_SIZE_RANGE,
            },
            "edge_label": None,
            "edge_color": {"type": "raw", "attribute": "color"},
            "edge_size": {
                "type": "continuous",
                "attribute": "size",
                "range": DEFAULT_EDGE_SIZE_RANGE,
            },
        }
    ).tag(sync=True)

    def __init__(
        self,
        graph,
        height=500,
        start_layout=False,
        node_color=None,
        node_size="size",
        node_size_range=DEFAULT_NODE_SIZE_RANGE,
        node_label="label",
        edge_color=None,
        edge_size="size",
        edge_size_range=DEFAULT_EDGE_SIZE_RANGE,
        edge_label=None,
        clickable_edges=False,
        process_gexf_viz=True,
        **kwargs
    ):
        super(Sigma, self).__init__(**kwargs)

        if height < 250:
            raise TypeError("Sigma widget cannot have a height < 250 px")

        # Own
        self.graph = graph

        # Traits
        self.height = height
        self.start_layout = start_layout
        self.snapshot = None
        self.layout = None
        self.clickable_edges = clickable_edges

        is_directed = isinstance(graph, DIRECTED_GRAPHS)
        is_multi = isinstance(graph, MULTI_GRAPHS)

        # Serializing graph as per graphology's JSON format
        nodes = []
        node_type = None

        for node, attr in graph.nodes.data():
            if node_type is None:
                node_type = type(node)

                if not isinstance(node, SUPPORTED_NODE_TYPES):
                    raise TypeError(
                        "ipysigma does not support graph with node keys which are not str, int or float (found a %s key)"
                        % node_type.__name__
                    )
            elif type(node) is not node_type:
                raise TypeError(
                    "ipysigma does not support mixed types for node keys (found %s and %s)"
                    % (node_type.__name__, type(node).__name__)
                )

            attr = attr.copy()

            if process_gexf_viz:
                process_node_gexf_viz(attr)

            serialized_node = {"key": node, "attributes": attr}

            nodes.append(serialized_node)

        edges = []

        for source, target, attr in graph.edges.data():
            attr = attr.copy()

            if process_gexf_viz:
                process_edge_gexf_viz(attr)

            # NOTE: networkx multigraph can have keys on edges, but they
            # are not required to be unique across the graph, which makes
            # them pointless for graphology, gexf etc.
            serialized_edge = {"source": source, "target": target, "attributes": attr}

            if not is_directed:
                serialized_edge["undirected"] = True

            edges.append(serialized_edge)

        # Serializing visual variables
        visual_variables = self.visual_variables.copy()

        # Nodes
        if node_color is not None:
            variable = {"type": "category"}

            resolve_variable_kwarg(nodes, variable, "node_color", node_color)

            visual_variables["node_color"] = variable

        if node_size is not None:
            variable = {"type": "continuous", "range": node_size_range}

            resolve_variable_kwarg(nodes, variable, "node_size", node_size)

            visual_variables["node_size"] = variable

        if node_label is not None:
            variable = {"type": "raw"}

            resolve_variable_kwarg(nodes, variable, "node_label", node_label)

            visual_variables["node_label"] = variable

        # Edges
        if edge_color is not None:
            variable = {"type": "category"}

            resolve_variable_kwarg(
                edges, variable, "edge_color", edge_color, allow_arbitrary_data=False
            )

            visual_variables["edge_color"] = variable

        if edge_size is not None:
            variable = {"type": "continuous", "range": edge_size_range}

            resolve_variable_kwarg(
                edges, variable, "edge_size", edge_size, allow_arbitrary_data=False
            )

            visual_variables["edge_size"] = variable

        if edge_label is not None:
            variable = {"type": "raw"}

            resolve_variable_kwarg(
                edges, variable, "edge_label", edge_label, allow_arbitrary_data=False
            )

            visual_variables["edge_label"] = variable

        self.visual_variables = visual_variables
        self.data = {
            "nodes": nodes,
            "edges": edges,
            "options": {
                "type": "directed" if is_directed else "undirected",
                "multi": is_multi,
            },
        }

    def __repr__(self):
        return "Sigma(nx.%s with %s nodes and %s edges)" % (
            self.graph.__class__.__name__,
            pretty_print_int(self.graph.order()),
            pretty_print_int(self.graph.size()),
        )

    def retrieve_layout(self):
        """
        Method returning the layout computed by ForceAtlas2 in the widget.

        Note that if the layout was never displayed, this method will return None.

        Also note that if you never ran the layout this method will return the
        initial layout that will be random in the [0, 1) range if you did not
        provide starting positions yourself.

        Returns:
            dict: a dictionary mapping node keys to {x, y} positions.
        """
        return self.layout

    def persist_layout(self):
        """
        Method applying the layout computed by ForceAtlas2 in the widget to
        the networkx graph passed as input to the widget.

        Note that it therefores mutates the networkx graph.

        Note that this method will raise an error if the widget was never displayed.
        """

        if self.layout is None:
            raise TypeError(
                "Widget did not compute any layout yet. Are you sure you displayed it?"
            )

        for node, attr in self.graph.nodes(data=True):
            pos = self.layout[node]
            attr["x"] = pos["x"]
            attr["y"] = pos["y"]

    def render_snasphot(self):
        """
        Method rendering and displaying a snasphot of the widget.

        This can be useful to save a version of the widget that can actually
        be seen in a static rendition of your notebook (when using nbconvert,
        for instance, or when reading the notebook on GitHub).

        Returns:
            Ipython.display.HTML: the snasphot as a data url in an img tag.
        """

        if not self.singleton_lock:
            raise TypeError(
                "Widget needs to be displayed on screen to render a snapshot. Maybe you reinstantiated it and forgot to display the new instance?"
            )

        self.snapshot = None

        html = HTML("<i>rendering snapshot...</i>")

        def update(change):
            html.value = '<img src="{}" style="max-width: 100%; height: auto; border: 1px solid #e0e0e0;">'.format(
                change.new
            )
            self.unobserve(update, "snapshot")

        self.observe(update, "snapshot")
        self.send({"msg": "render_snapshot"})

        return html
