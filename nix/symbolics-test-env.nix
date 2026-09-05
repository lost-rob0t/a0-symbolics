{ pkgs }:
let
  python = import ./python-env.nix {
    inherit pkgs;
    focused = true;
  };
in
pkgs.buildEnv {
  name = "a0-symbolics-focused-test-env";
  paths = [ python pkgs.swi-prolog ];
}
