{self, ...}: {
  perSystem = {
    pkgs,
    self',
    ...
  }: {
    packages.default = self'.packages.nix-visualize;
    packages.nix-visualize = pkgs.python3Packages.callPackage ./derivation.nix {inherit self;};
  };
}
