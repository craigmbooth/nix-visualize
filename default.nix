{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python3Packages
}:

pythonPackages.buildPythonPackage rec {
  name = "nix-visualize-${version}";
  version = "1.0.5";
  src = ./.;
  propagatedBuildInputs = with pythonPackages; [
    matplotlib
    networkx
    pygraphviz
    pandas
  ];
}
