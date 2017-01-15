"""Definitions for edges and nodes for Nix dependency visualizer"""

import os
import util

class Edge(object):
    """Class represents the relationship between two packages."""

    def __init__(self, node_from, node_to):
        self.nfrom_raw=node_from
        self.nto_raw=node_to
        self.nfrom = util.remove_nix_hash(os.path.basename(self.nfrom_raw))
        self.nto = util.remove_nix_hash(os.path.basename(self.nto_raw))

    def __repr__(self):
        return "{} -> {}".format(self.nfrom, self.nto)


class Node(object):
    """Class represents an individual package"""

    def __init__(self, name):
        self.raw_name = name
        self.name = util.remove_nix_hash(self.raw_name)
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

    def add_level(self, debug=False):
        """Add the Node's level.  Level is this package's position in the
        hierarchy.  0 is the top-level package.  That package's dependencies
        are level 1, their dependencies are level 2.
        """


        if self.level >= 0:
            if debug is True:
                print "Found that {} as level {}".format(self.name, self.level)
            return self.level

        elif len(self.parents) > 0:
            if debug is True:
                print "Adding level to {}, with parents: {}".format(
                    self.name, self.parents)

            parent_levels =  [p.add_level(debug=debug) for p in self.parents]
            self.level = max(parent_levels) + 1
            return self.level
        else:
            self.level = 0
            return 0

    def __repr__(self):

        n = self.name
        if n.startswith("narrativescience-"):
            n = n.lstrip("narrativescience-")

        if self.name == "python3.4-ns_python_runtime-0.0.561":
            return "Quill 3 Python Container"
        elif self.name == "narrativescience-quill3-singlejs-0.0.0-nodejs-4.6.0":
            return "Quill 3 Node.js Container"
        elif n.endswith("-nodejs-4.6.0"):
            return n.replace("-nodejs-4.6.0", "")
        elif n.startswith("python3.4-"):
            return n.replace("python3.4-", "")
        else:
            return n

    def __hash__(self):
        return hash((self.name,))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name
        else:
            return False
