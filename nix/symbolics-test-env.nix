{ pkgs }:
import ./python-env.nix {
  inherit pkgs;
  focused = true;
}
