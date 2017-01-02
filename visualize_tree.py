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

import networkx as nx
import pygraphviz as pgv
import matplotlib.pyplot as plt

import util
from graph_objects import Node, Edge

#: Default values for things we expect in the config file
CONFIG_OPTIONS = {
    "aspect_ratio": (2, int),
    "style_scale": (1.0, float),
    "edge_color": ("#888888", str),
    "y_sublevels": (5, int),
    "y_sublevel_spacing": (0.2, float),
    "num_iterations": (100, int),
    "max_displacement": (2.5, float),
    "repulsive_force_normalization": (2.0, float),
    "attractive_force_normalization": (1.0, float)
}

class Graph(object):

    def __init__(self, package, config, output_file, do_write=True):

        self.config = self._parse_config(config)

        self.nodes = []
        self.edges = []

        self.root_package_name = util.remove_nix_hash(os.path.basename(package))

        # Run nix-store -q --graph <package>.  This generates a graphviz
        # file with package dependencies
        cmd = ("/nix/store/lzradzr5c38amahvqfra9g7rp8wfw2f0-nix-1.11.4/"
              "bin/nix-store -q --graph {}".format(package))
        res = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        raw_graph, _ = res.communicate()

        self.nodes, self.edges = self._get_edges_and_nodes(raw_graph)

        self._add_edges_to_nodes()

        # The package itself is level 0, its direct dependencies are
        # level 1, their direct dependencies are level 2, etc.
        for n in self.nodes:
            n.add_level()

        self.depth = max([x.level for x in self.nodes]) + 1

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

        configfile = config[0]
        configsection = config[1]

        return_configs = {}

        if configfile is not None:
            configs = ConfigParser.ConfigParser()
            configs.read(configfile)
            if len(configs.sections()) > 1:
                if configsection is None:
                    raise util.TreeCLIError("Config file {} contains more than "
                                       "one section, so -s must be set")
            else:
                configsection = configs.sections()[0]

        for param, (p_default, p_dtype) in CONFIG_OPTIONS.iteritems():
            try:
                return_configs[param] = p_dtype(
                    configs.get(configsection, param))
            except ConfigParser.NoOptionError:
                return_configs[param] = p_dtype(p_default)
                if verbose is True:
                    print "Adding default of {} for {}".format(
                        p_dtype(p_default), param)

        return return_configs

    def write_frame_png(self, filename="frame.png"):

        pos = {n: (n.x, n.y) for n in self.nodes}
        col = [x.level for x in self.G.nodes()]

        img_y_height=24
        # MORE PARAMETERS HERE!
        size_per_out = 200   #PARAMETER

        size_min = 300 * self.config["style_scale"]
        size_max = 5.0 * size_min  #PARAMETER

        plt.figure(1, figsize=(img_y_height*self.config["aspect_ratio"],
                               img_y_height))
        node_size = [min(size_min + (x.out_degree-1)*size_per_out,
                         size_max) for x in self.G.nodes()]

        nx.draw(self.G, pos, node_size=node_size,  arrows=False,
             with_labels=True, edge_color=self.config["edge_color"],
             font_size=12*self.config["style_scale"],
             node_color=col, vmin=0, vmax=self.depth, alpha=0.3, nodelist=[])

        nx.draw(self.G, pos, node_size=node_size,  arrows=False,
             with_labels=True,
             font_size=12*self.config["style_scale"],
             node_color=col, vmin=0, vmax=self.depth, edgelist=[])
        print "Writing: {}".format(filename)
        plt.savefig(filename, dpi=75)
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
           * XXXXX
        """

        #: The distance between levels in arbitrary units.  Used to set a
        #: scale on the diagram
        level_height = 10

        # Time to integrate for
        tmax = 30.0

        #: Maximum displacement of a point on a single iteration
        max_displacement = level_height * self.config["max_displacement"]

        #: The timestep to take on each iteration
        dt = tmax/self.config["num_iterations"]

        # Initialize x with a random position unless you're the top level
        # package, then set x=0
        for n in self.nodes:
            if n.level == 0:
                n.x = 500
                n.y = self.depth * level_height
            else:
                n.x = 1000*random.random()

        iframe = 0
        for iternum in range(self.config["num_iterations"]):

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


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("package",
                        help="Full path to a package in the Nix store. "
                        "This package will be diagrammed")
    parser.add_argument("--configfile", "-c", help="ini file with layout and "
                        "style configuration", required=False)
    parser.add_argument("--configsection", "-s", help="section from ini file "
                        "to read")
    parser.add_argument("--output", "-o", help="output filename, will be "
                        "a png", default="frame.png", required=False)
    args = parser.parse_args()

    graph = Graph(args.package, (args.configfile, args.configsection),
                  args.output)
