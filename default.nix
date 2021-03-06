{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python2Packages
}:

pythonPackages.buildPythonPackage rec {
  name = "nix-visualize-${version}";
  version = "1.0.4";
  src = ./.;
  propagatedBuildInputs = with pythonPackages; [
    matplotlib
    networkx
    pygraphviz
  ];
}
