# Nix Dependency Visualizer

Script that automates the generation of pretty dependency graphs from the output of ``nix-store -q --graph <package>``.

## Command Line Options

## Configuration Files

## Graph Layout Algorithm

### Vertical Positioning:  Levels

 Since dependency trees are acyclic, it is possible to sort the tree so that *every package appears below everything it depends on*.  The first step of the graph layout is to perform this sort, which I refer to in the code as adding "levels" to packages.  The bottom of the tree, level *n*, consists of any packages that can be built without any external dependencies.  The level above that, level *n-1* contains any packages that can be built using only packages on level *n*.  The level above that, *n-2*, contains any packages that can be built using only packages on levels *n-1* and *n*.  In this way, all packages on the tree sit above any of their dependencies, and the package we're diagramming out sits at the top of the tree.

![Demonstration of leveling algorithm](images/levels.png)


#### Adding random offsets
