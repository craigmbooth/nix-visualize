# Nix Dependency Visualizer

Script that automates the generation of pretty dependency graphs from the output of ``nix-store -q --graph <package>``.

## Example Images

<img src="images/nix.png" width="33%"><img src="images/dbs.png" width="66%">

## Command Line Options

After installation, the minimal way to run the CLI is

    nix-visualize <path-to-nix-store-object>

which will generate a graph of the dependency tree for the nix store object using sensible defaults for both appearance and graph layout.  In order to override settings, use a configuration file in .ini format.

    usage: nix-visualize [-h] [--configfile CONFIGFILE]
                         [--configsection CONFIGSECTION] [--output OUTPUT]
                         <path-to-nix-store-object>

## Configuration Files

If there is only a single section in the configuration file, it is only necessary to specify the ``--configfile`` option.  If the config file contains more than one section it is also necessary to specify ``--configsection``.

### List of parameters

    * `aspect_ratio [default 2.0]`: Ratio of x size of image to y size
    * `dpi [default 300]`: pixels per inch
    * `img_y_height_inches [default 24]`: size of the output image y dimension in inches
    * `font_scale [default 1.0]`: fonts are printed at size 12*font_scale
    * `color_scatter [default 1.0]`: The amount of randomness in the colors.  If this is zero, all nodes on the same level are the same color.
    * `edge_color [default #888888]`: Hex code for color of lines linking nodes
    * `font_color [default #888888]`: Hex code for color of font labeling nodes
    * `edge_alpha [default 0.3]`: Opacity of edges. 1.0 is fully opaque, 0.0 is transparent
    * `show_labels [default 1]`: If this is 0 then hide labels
    * `y_sublevels [default 5]`:
    * `color_map [default XXXX]`: http://matplotlib.org/examples/color/colormaps_reference.html
    * `y_sublevel_spacing [default 0.2]`:
    * `num_iterations [default 100]`:
    * `max_displacement [default 2.5]`:
    * `repulsive_force_normalization [default 2.0]`:
    * `attractive_force_normalization [default 1.0]`:
    * `add_size_per_out_link [default 200]`:
    * `max_node_size_over_min_node_size [default 5.0]`:
    * `min_node_size [default 100.0]`:
    * `tmax [default 30.0]`:

## Graph Layout Algorithm

Packages are sorted vertically such that all packages are above everything that they depend upon, and horizontally so that they are close to their direct requirements, while not overlapping more than is necessary.

### Vertical Positioning

 Since dependency trees are acyclic, it is possible to sort the tree so that *every package appears below everything it depends on*.  The first step of the graph layout is to perform this sort, which I refer to in the code as adding "levels" to packages.  The bottom of the tree, level *n*, consists of any packages that can be built without any external dependencies.  The level above that, level *n-1* contains any packages that can be built using only packages on level *n*.  The level above that, *n-2*, contains any packages that can be built using only packages on levels *n-1* and *n*.  In this way, all packages on the tree sit above any of their dependencies, and the package we're diagramming out sits at the top of the tree.

<img src="images/levels.png" width="50%" align="middle">

#### Adding vertical offsets

In order to keep labels legible, after putting the packages on levels, some of them are given a small vertical offset.  This is done by sorting each level by x-position, and then

<img src="images/sublevels.png">

### Horizontal Positioning

Initially the horizontal positions for packages are chosen randomly, but the structure of the underlying graph is made clearer if we try to optimize for two things:

1. A package should be vertically aligned with the things it depends upon (i.e. the nodes on the level above it that it is linked to), in order to minimize edge crossing as far as possible
2. A package should try not to be too close to another package on the same level, so as not to have nodes overlap.

<img src="images/horizontal.png" align="middle">
