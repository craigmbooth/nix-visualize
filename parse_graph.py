"""Script that visualizes dependencies of Nix packages"""
import argparse
import ConfigParser
import itertools
import os
import random
import shlex
import subprocess

import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CONFIG_OPTIONS = {
    "aspect_ratio": (2, int),
    "style_scale": (1.0, float),
    "edge_color": ("#888888", str)
    }

class TreeCLIError(Exception):
    pass


def remove_nix_hash(string):
    """Given a nix store name of the form <hash>-<packagename>, remove
    the hash
    """
    return "-".join(string.split("-")[1:])


class Edge(object):
    """Class represents the relationship between two packages."""

    def __init__(self, node_from, node_to):
        self.nfrom_raw=node_from
        self.nto_raw=node_to
        self.nfrom = remove_nix_hash(os.path.basename(self.nfrom_raw))
        self.nto = remove_nix_hash(os.path.basename(self.nto_raw))

    def __repr__(self):
        return "{} -> {}".format(self.nfrom, self.nto)


class Node(object):
    """Class represents an individual package"""

    def __init__(self, name):
        self.raw_name = name
        self.name = remove_nix_hash(self.raw_name)
        self.children = []
        self.parents = []
        self.in_degree = 0
        self.out_degree = 0
        self.level = -1

        self.x = 0
        self.y = 0

    def add_parent(self, nfrom, nto):
        self.parents.append(nto)
        self.out_degree = len(self.parents)

    def add_child(self, nfrom, nto):
        self.children.append(nfrom)
        self.in_degree = len(self.children)


    def add_level(self):
        """Add the Node's level.  Level is this package's position in the
        hierarchy.  0 is the top-level package.  That package's dependencies
        are level 1, their dependencies are level 2.
        """
        if self.level >= 0:
            return self.level
        if len(self.parents) > 0:
            parent_levels =  [p.add_level() for p in self.parents]
            self.level = max(parent_levels) + 1
            return self.level
        else:
            self.level = 0
            return 0

    def __repr__(self):
        return self.name
        if not self.name.startswith("nodejs"):
            return self.name.strip("-nodejs-4.6.0")
        else:
            return self.name


class Graph(object):

    def __init__(self, package, config, output_file, do_write=True):

        self.config = self._parse_config(config)

        self.nodes = []
        self.edges = []

        # Run nix-store -q --graph <package>.  This generates a graphviz
        # file with package dependencies
        cmd = ("/nix/store/lzradzr5c38amahvqfra9g7rp8wfw2f0-nix-1.11.4/"
              "bin/nix-store -q --graph {}".format(package))
        res = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        raw_graph, _ = res.communicate()

        self.root_package_name = remove_nix_hash(os.path.basename(package))

        self.nodes, self.edges = self._get_edges_and_nodes(raw_graph)

        self._add_edges_to_nodes()

        # The package itself is level 0, its direct dependencies are
        # level 1, their direct dependencies are level 2, etc.
        for n in self.nodes:
            n.add_level()

        # The depth of the tree is simply 1 + the maximum level since
        # the root is level 0
        self.depth = max([x.level for x in self.nodes]) + 1

        # Transform the Nodes and Edges into a networkx graph
        self.G = nx.DiGraph()
        for node in self.nodes:
            self.G.add_node(node)
            for parent in node.parents:
                self.G.add_edge(node, parent)

        self._add_pos_to_nodes()

        if do_write is True:
            self.write_frame(filename=output_file)

    def _parse_config(self, config, verbose=True):

        configfile = config[0]
        configsection = config[1]

        return_configs = {}

        if configfile is not None:
            configs = ConfigParser.ConfigParser()
            configs.read(configfile)
            if len(configs.sections()) > 1:
                if configsection is None:
                    raise TreeCLIError("Config file {} contains more than "
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

    def write_frame(self, filename="frame.png"):

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


        #: The distance between levels in arbitrary units.  Used to set a
        #: scale on the diagram
        level_height = 10

        # Time to integrate for
        tmax = 30.0

        #: Number of y-splits for each level
        y_levels = 5
        #: Fraction of a level that each split is
        y_space = 0.2
        #: Maximum number of iterations to perform
        num_iterations = 600

        #: Maximum displacement of a point on a single iteration
        max_displacement = level_height * 2.5

        #: Factor by which we boost the repulsive force
        norml_sib = 10

        dt = tmax/num_iterations

        # y position is easy, just use the level.  Initialize x with
        # a random position unless you're the top level package, then
        # put it in the middle
        for n in self.nodes:
            n.y = (self.depth - n.level) * level_height
            if n.level == 0:
                n.x = 0
            else:
                n.x = 1000*(random.random())

        iframe = 0
        for iternum in range(num_iterations):

            total_abs_displacement = 0.0

            for level in range(self.depth):
                if level == 0:
                    continue

                # Get the y-offset by cycling with other nodes in the
                # same level
                xpos = [(x.name, x.x) for x in self.level(level)]
                xpos = sorted(xpos, key=lambda x:x[1])
                xpos = zip(xpos, itertools.cycle(range(y_levels)))
                pos_sorter = {x[0][0]: x[1] for x in xpos}

                for n in self.level(level):
                    n.y = ((self.depth - n.level) * level_height +
                           pos_sorter[n.name]*y_space*level_height)


                for lev_node in self.level(level):

                    # We pull nodes toward their parents
                    dis = [parent.x - lev_node.x for
                           parent in lev_node.parents]

                    sibs = self.level(level)
                    sdis = [1.0/(sib.x - lev_node.x) for
                            sib in sibs if abs(sib.x-lev_node.x) > 1e-3]

                    total_sdis = sum(sdis) * norml_sib
                    total_displacement = float(sum(dis)) / len(dis)

                    if total_displacement > max_displacement:
                        dx_parent = max_displacement
                    elif total_displacement < -max_displacement:
                        dx_parent = -max_displacement
                    else:
                        dx_parent = total_displacement

                    if total_sdis > max_displacement:
                        dx_sibling = max_displacement
                    elif total_sdis < -max_displacement:
                        dx_sibling = -max_displacement
                    else:
                        dx_sibling = total_sdis

                    lev_node.dx_parent = dx_parent
                    lev_node.dx_sibling = -dx_sibling


                for lev_node in self.level(level):
                    lev_node.x += lev_node.dx_parent * dt
                    lev_node.x += lev_node.dx_sibling * dt
                    total_abs_displacement += abs(lev_node.dx_parent * dt)
                    total_abs_displacement += abs(lev_node.dx_sibling * dt)

            #print "In iteration {}, total displacement: {}".format(iternum,
            #          total_abs_displacement)


    def level(self, level):
        """Return a list of all nodes on a given level
        """
        return [x for x in self.nodes if x.level == level]

    def levels(self, min_level=0):
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
        all_edges = []
        all_nodes = []

        for raw_line in raw_lines.split("\n"):
            raw_line = raw_line.rstrip("\n")

            if raw_line.startswith("digraph"):
                continue

            # This is a dumb heuristic, but ensures that we don't have the
            # "Grammar" lines in there like closing brackets, etc.
            if len(raw_line) < 5:
                continue

            if "->" in raw_line:
                parts = raw_line.split(" ")
                nfrom = parts[0].replace('"', "")
                nto = parts[2].replace('"', "")
                all_edges.append(Edge(nfrom, nto))
            else:
                parts = raw_line.split(" ")
                name = parts[0].replace('"', "")
                if remove_nix_hash(name) not in [n.name for n in all_nodes]:
                    all_nodes.append(Node(name))

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

            nfrom.add_parent(nfrom, nto)
            nto.add_child(nfrom, nto)

    def __repr__(self):
        """Basic print of Graph, show the package name and the number of
        dependencies on each level
        """

        head = self.level(0)
        ret_str = "Graph of package: {}".format(head[0].name)
        ilevel = 1
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
