{
  lib,
  buildPythonPackage,
  matplotlib,
  networkx,
  pygraphviz,
  pandas,
  self,
}:
buildPythonPackage {
  pname = "nix-visualize";
  version = "1.0.5";
  src = lib.cleanSource self;

  propagatedBuildInputs = [
    matplotlib
    networkx
    pygraphviz
    pandas
  ];
}
