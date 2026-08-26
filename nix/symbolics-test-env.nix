{ pkgs }:
let
  ps = pkgs.python312Packages;
  packages = with ps; [
    flask
    litellm
    markdown
    pydantic
    python-dotenv
    pytest
    pytest-asyncio
    pytest-mock
    tiktoken
  ];
in
pkgs.python312.withPackages (_: packages)
