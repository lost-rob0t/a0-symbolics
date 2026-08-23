{ pkgs, ... }:
{
  home.username = "root";
  home.homeDirectory = "/root";
  home.stateVersion = "26.05";

  home.packages = with pkgs; [
    bashInteractive
    bat
    cron
    curl
    eza
    fd
    file
    fzf
    gcc
    gh
    git
    gnumake
    jq
    nodejs
    openssh
    pkg-config
    procps
    python3
    ripgrep
    rsync
    sbcl
    swipl
    tmux
    tree
    unzip
    uv
    wget
    which
    zip
  ];

  programs.home-manager.enable = true;
}
