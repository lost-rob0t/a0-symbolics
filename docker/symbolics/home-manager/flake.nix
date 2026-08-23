{
  description = "Default persistent Home Manager profile for a0-symbolics";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, home-manager, ... }:
    let
      mkHome = system:
        home-manager.lib.homeManagerConfiguration {
          pkgs = nixpkgs.legacyPackages.${system};
          modules = [ ./home.nix ];
        };
    in {
      homeConfigurations = {
        root-x86_64-linux = mkHome "x86_64-linux";
        root-aarch64-linux = mkHome "aarch64-linux";
      };
    };
}
