"""Script that visualizes dependencies of Nix packages"""
import argparse
import ConfigParser
import itertools
import os
import random
import shlex
import subprocess
import sys
import tempfile
import logging

import networkx as nx
import pygraphviz as pgv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

import nix_visualize

import util
from graph_objects import Node, Edge

logger = logging.getLogger(__name__)

#: Default values for things we expect in the config file
CONFIG_OPTIONS = {
    "aspect_ratio": (2, float),
    "dpi": (300, int),
    "font_scale": (1.0, float),
    "color_scatter": (1.0, float),
    "edge_color": ("#888888", str),
    "font_color": ("#888888", str),
    "color_map": ("rainbow", str),
    "img_y_height_inches": (24, float),
    "y_sublevels": (5, int),
    "y_sublevel_spacing": (0.2, float),
    "num_iterations": (100, int),
    "edge_alpha": (0.3, float),
    "max_displacement": (2.5, float),
    "top_level_spacing": (100, float),
    "repulsive_force_normalization": (2.0, float),
    "attractive_force_normalization": (1.0, float),
    "add_size_per_out_link": (200, int),
    "max_node_size_over_min_node_size": (5.0, float),
    "min_node_size": (100.0, float),
    "tmax": (30.0, float),
    "show_labels": (1, int)
}


class Graph(object):
    """Class representing a dependency tree"""

    def __init__(self, packages, config, output_file, do_write=True):
        """Initialize a graph from the result of a nix-store command"""

        self.config = self._parse_config(config)

        self.nodes = []
        self.edges = []

        self.root_package_names = [util.remove_nix_hash(os.path.basename(x)) for
                                   x in packages]

        for package in packages:
            # Run nix-store -q --graph <package>.  This generates a graphviz
            # file with package dependencies
            cmd = ("nix-store -q --graph {}".format(package))
            res = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

            stdout, stderr = res.communicate()

            if res.returncode != 0:
                raise util.TreeCLIError("nix-store call failed, message "
                                        "{}".format(stderr))

            package_nodes, package_edges = self._get_edges_and_nodes(stdout)

            self.nodes.extend(package_nodes)
            self.edges.extend(package_edges)

        self.nodes = list(set(self.nodes))

        self._add_edges_to_nodes()

        # The package itself is level 0, its direct dependencies are
        # level 1, their direct dependencies are level 2, etc.
        for n in self.nodes:
            n.add_level()

        self.depth = max([x.level for x in self.nodes]) + 1

        logger.info("Graph has {} nodes, {} edges and a depth of {}".format(
                    len(self.nodes), len(self.edges), self.depth))

        # Transform the Nodes and Edges into a networkx graph
        self.G = nx.DiGraph()
        for node in self.nodes:
            self.G.add_node(node)
            for parent in node.parents:
                self.G.add_edge(node, parent)

        self._add_pos_to_nodes()
        if do_write is True:
            self.write_frame_png(filename=output_file)

    def _parse_config(self, config, verbose=True):
        """Load visualization parameters from config file or take defaults
        if they are not in there
        """

        configfile = config[0]
        configsection = config[1]

        return_configs = {}

        if configfile is not None:
            configs = ConfigParser.ConfigParser()
            configs.read(configfile)
            if len(configs.sections()) > 1:
                if configsection is None:
                    raise util.TreeCLIError("Config file {} contains more than "
                                       "one section, so -s must be set".format(
                                           configfile))
                elif configsection not in configs.sections():
                    raise util.TreeCLIError("Config file {} does not contain a "
                                            "section named {}".format(
                                                configfile, configsection))
            else:
                # There is only one section in the file, just read it
                configsection = configs.sections()[0]
        else:
            logger.info("--configfile not set, using all defaults")
            return {k: v[0] for k, v in CONFIG_OPTIONS.iteritems()}

        logger.info("Reading section [{}] of file {}".format(configsection,
                                                             configfile))
        # Loop through config options.  If there is a corresponding key in the
        # config file, overwrite, else take the value from the defaults
        for param, (p_default, p_dtype) in CONFIG_OPTIONS.iteritems():
            try:
                return_configs[param] = p_dtype(
                    configs.get(configsection, param))
                logger.debug("Setting {} to {}".format(param,
                                                       return_configs[param]))
            except (ConfigParser.NoOptionError, ValueError):
                return_configs[param] = p_dtype(p_default)
                logger.info( "Adding default of {} for {}".format(
                    p_dtype(p_default), param))

        return return_configs

    def write_frame_png(self, filename="frame.png"):
        """Dump the graph to a png file"""

        try:
            cmap = getattr(matplotlib.cm, self.config["color_map"])
        except AttributeError:
            raise util.TreeCLIError("Colormap {} does not exist".format(
                self.config["color_map"]))

        pos = {n: (n.x, n.y) for n in self.nodes}
        col_scale = 255.0/(self.depth+1.0)
        col = [(x.level+random.random()*self.config["color_scatter"])*col_scale
               for x in self.G.nodes()]
        col = [min([x,255]) for x in col]

        img_y_height=self.config["img_y_height_inches"]

        size_min = self.config["min_node_size"]
        size_max = self.config["max_node_size_over_min_node_size"] * size_min

        plt.figure(1, figsize=(img_y_height*self.config["aspect_ratio"],
                               img_y_height))
        node_size = [min(size_min + (x.out_degree-1)*
                         self.config["add_size_per_out_link"],
                         size_max) if x.level > 0 else size_max for
                     x in self.G.nodes()]

        # Draw edges
        nx.draw(self.G, pos, node_size=node_size,  arrows=False,
             with_labels=self.config["show_labels"],
             edge_color=self.config["edge_color"],
             font_size=12*self.config["font_scale"],
             node_color=col, vmin=0, vmax=256,
             alpha=self.config["edge_alpha"], nodelist=[])

        # Draw nodes
        nx.draw(self.G, pos, node_size=node_size,  arrows=False,
             with_labels=self.config["show_labels"],
             font_size=12*self.config["font_scale"],
             node_color=col, vmin=0, vmax=255, edgelist=[],
             font_weight="light", cmap=cmap,
             font_color=self.config["font_color"])

        logger.info("Writing png file: {}".format(filename))
        plt.savefig(filename, dpi=self.config["dpi"])
        plt.close()

    def _add_pos_to_nodes(self):
        """Populates every node with an x an y position using the following
        iterative algorithm:

           * start at t=0
           * Apply an x force to each node that is proportional to the offset
             between its x position and the average position of its parents
           * Apply an x force to each node that pushes it away from its siblings
             with a force proportional to 1/d, where d is the distance between
             the node and its neighbor
           * advance time forward by dt=tmax/num_iterations, displace particles
             by F*dt
           * repeat until the number of iterations has been exhausted
        """

        logger.info("Adding positions to nodes")

        #: The distance between levels in arbitrary units.  Used to set a
        #: scale on the diagram
        level_height = 10

        #: Maximum displacement of a point on a single iteration
        max_displacement = level_height * self.config["max_displacement"]

        #: The timestep to take on each iteration
        dt = self.config["tmax"]/self.config["num_iterations"]

        number_top_level = len([x for x in self.nodes if x.level == 0])

        count_top_level = 0
        # Initialize x with a random position unless you're the top level
        # package, then space nodes evenly
        for n in self.nodes:
            if n.level == 0:
                n.x = float(count_top_level)*self.config["top_level_spacing"]
                count_top_level += 1
                n.y = self.depth * level_height
            else:
                n.x = ((number_top_level + 1) *
                       self.config["top_level_spacing"] * random.random())

        for iternum in range(self.config["num_iterations"]):
            if iternum in range(0,self.config["num_iterations"],
                                int(self.config["num_iterations"]/10)):
                logger.debug("Completed iteration {} of {}".format(iternum,
                    self.config["num_iterations"]))
            total_abs_displacement = 0.0

            for level in range(1, self.depth):

                # Get the y-offset by cycling with other nodes in the
                # same level
                xpos = [(x.name, x.x) for x in self.level(level)]
                xpos = sorted(xpos, key=lambda x:x[1])
                xpos = zip(xpos,
                           itertools.cycle(range(self.config["y_sublevels"])))
                pos_sorter = {x[0][0]: x[1] for x in xpos}

                for n in self.level(level):
                    n.y = ((self.depth - n.level) * level_height +
                           pos_sorter[n.name] *
                           self.config["y_sublevel_spacing"]*level_height)


                for lev_node in self.level(level):
                    # We pull nodes toward their parents
                    dis = [parent.x - lev_node.x for
                           parent in lev_node.parents]

                    # And push nodes away from their siblings with force 1/r
                    sibs = self.level(level)
                    sdis = [1.0/(sib.x - lev_node.x) for
                            sib in sibs if abs(sib.x-lev_node.x) > 1e-3]

                    total_sdis = (
                        sum(sdis) *
                        self.config["repulsive_force_normalization"])
                    total_displacement = (
                        self.config["attractive_force_normalization"] *
                        float(sum(dis)) / len(dis))

                    # Limit each of the displacements to the max displacement
                    dx_parent = util.clamp(total_displacement, max_displacement)
                    lev_node.dx_parent = dx_parent

                    dx_sibling = util.clamp(total_sdis, max_displacement)
                    lev_node.dx_sibling = -dx_sibling

                for lev_node in self.level(level):
                    lev_node.x += lev_node.dx_parent * dt
                    lev_node.x += lev_node.dx_sibling * dt
                    total_abs_displacement += (abs(lev_node.dx_parent * dt) +
                                               abs(lev_node.dx_sibling * dt))

    def level(self, level):
        """Return a list of all nodes on a given level
        """
        return [x for x in self.nodes if x.level == level]

    def levels(self, min_level=0):
        """An iterator over levels, yields all the nodes in each level"""
        for i in range(min_level,self.depth):
            yield self.level(i)

    def nodes_by_prefix(self, name):
        """Return a list of all nodes whose names begin with a given prefix
        """
        return [x for x in self.nodes if x.name.startswith(name)]

    def _get_edges_and_nodes(self, raw_lines):
        """Transform a raw GraphViz file into Node and Edge objects.  Note
        that at this point the nodes and edges are not linked into a graph
        they are simply two lists of items."""

        tempf = tempfile.NamedTemporaryFile(delete=False)
        tempf.write(raw_lines)
        tempf.close()
        G = pgv.AGraph(tempf.name)

        all_edges = []
        all_nodes = []

        for node in G.nodes():
            if (util.remove_nix_hash(node.name) not
                in [n.name for n in all_nodes]):
                all_nodes.append(Node(node.name))

        for edge in G.edges():
            all_edges.append(Edge(edge[0], edge[1]))

        return all_nodes, all_edges

    def _add_edges_to_nodes(self):
        """Given the lists of Edges and Nodes, add parents and children to
        nodes by following each edge
        """

        for edge in self.edges:
            nfrom = [n for n in self.nodes if n.name == edge.nfrom]
            nto = [n for n in self.nodes if n.name == edge.nto]
            nfrom = nfrom[0]
            nto = nto[0]

            if nfrom.name == nto.name:
                # Disallow self-references
                continue

            if nto not in nfrom.parents:
                nfrom.add_parent(nfrom, nto)
            if nfrom not in nto.children:
                nto.add_child(nfrom, nto)

    def __repr__(self):
        """Basic print of Graph, show the package name and the number of
        dependencies on each level
        """
        head = self.level(0)
        ret_str = "Graph of package: {}".format(head[0].name)
        for ilevel, level in enumerate(self.levels(min_level=1)):
            ret_str += "\n\tOn level {} there are {} packages".format(
                ilevel+1, len(level))
        return ret_str


def init_logger(debug=False):
    """Sets up logging for this cli"""
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format="%(levelname)s %(message)s\033[1;0m",
                        stream=sys.stderr, level=log_level)
    logging.addLevelName(logging.CRITICAL,
                         "\033[1;37m[\033[1;31mCRIT\033[1;37m]\033[0;31m")
    logging.addLevelName(logging.ERROR,
                         "\033[1;37m[\033[1;33mERR \033[1;37m]\033[0;33m")
    logging.addLevelName(logging.WARNING,
                         "\033[1;37m[\033[1;33mWARN\033[1;37m]\033[0;33m")
    logging.addLevelName(logging.INFO,
                         "\033[1;37m[\033[1;32mINFO\033[1;37m]\033[0;37m")
    logging.addLevelName(logging.DEBUG,
                         "\033[1;37m[\033[1;34mDBUG\033[1;37m]\033[0;34m")


def main():
    """Parse command line arguments, instantiate graph and dump image"""
    parser = argparse.ArgumentParser()
    parser.add_argument("packages",
                        help="Full path to a package in the Nix store. "
                        "This package will be diagrammed", nargs='+')
    parser.add_argument("--configfile", "-c", help="ini file with layout and "
                        "style configuration", required=False)
    parser.add_argument("--configsection", "-s", help="section from ini file "
                        "to read")
    parser.add_argument("--output", "-o", help="output filename, will be "
                        "a png", default="frame.png", required=False)
    parser.add_argument('--verbose', dest='verbose', action='store_true')
    parser.add_argument('--no-verbose', dest='verbose', action='store_false')
    parser.set_defaults(verbose=False)
    args = parser.parse_args()

    init_logger(debug=args.verbose)

    try:
        graph = Graph(args.packages, (args.configfile, args.configsection),
                  args.output)
    except util.TreeCLIError, e:
        sys.stderr.write("ERROR: {}\n".format(e.message))
        sys.exit(1)


if __name__ == "__main__":
    main()
