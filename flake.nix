{
  description = "Agent Zero with Prolog-RLM symbolic context integration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    prolog-rlm.url = "github:lost-rob0t/prolog-rlm?ref=codex/sol-high-integration";
    prolog-rlm.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, prolog-rlm }:
    let
      systems = [ "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = import ./nix/python-env.nix { inherit pkgs; };
          prologRlm = prolog-rlm.packages.${system}.default;
          source = pkgs.stdenvNoCC.mkDerivation {
            pname = "a0-symbolics-source";
            version = "0.1.0";
            src = nixpkgs.lib.cleanSourceWith {
              src = self;
              filter = path: type:
                let name = baseNameOf path;
                in !(builtins.elem name [ ".git" ".direnv" ".env" "usr" "tmp" "__pycache__" ".pytest_cache" ]);
            };
            dontBuild = true;
            installPhase = ''
              mkdir -p "$out/share/a0-symbolics"
              cp -R . "$out/share/a0-symbolics/"
            '';
          };
          app = pkgs.writeShellApplication {
            name = "a0-symbolics";
            runtimeInputs = [ pkgs.coreutils python pkgs.swi-prolog prologRlm ];
            text = ''
              state_dir="''${A0_STATE_DIR:-''${XDG_DATA_HOME:-$HOME/.local/share}/a0-symbolics}"
              source_root="${source}/share/a0-symbolics"
              runtime_root="$state_dir/runtime/$(basename "${source}")"
              mkdir -p "$runtime_root" "$state_dir/usr" "$state_dir/tmp"
              for entry in "$source_root"/*; do
                name="$(basename "$entry")"
                if [ "$name" != usr ] && [ "$name" != tmp ]; then
                  ln -sfn "$entry" "$runtime_root/$name"
                fi
              done
              ln -sfn "$state_dir/usr" "$runtime_root/usr"
              ln -sfn "$state_dir/tmp" "$runtime_root/tmp"
              export TMPDIR="$state_dir/tmp"
              export PROLOG_RLM_ENABLED="''${PROLOG_RLM_ENABLED:-1}"
              export SWIPL_PACK_PATH="${prologRlm}/share/swi-prolog/pack''${SWIPL_PACK_PATH:+:$SWIPL_PACK_PATH}"
              cd "$runtime_root"
              exec ${python}/bin/python "$source_root/run_ui.py" "$@"
            '';
          };
        in {
          inherit source;
          prolog-rlm = prologRlm;
          default = app;
          a0-symbolics = app;
          python-runtime = python;
        });

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/a0-symbolics";
        };
      });

      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = self.packages.${system}.python-runtime;
          prologRlm = prolog-rlm.packages.${system}.default;
        in {
          default = pkgs.mkShell {
            packages = [ python pkgs.swi-prolog prologRlm ];
            PROLOG_RLM_ENABLED = "1";
            SWIPL_PACK_PATH = "${prologRlm}/share/swi-prolog/pack";
          };
        });

      checks = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = self.packages.${system}.python-runtime;
          prologRlm = prolog-rlm.packages.${system}.default;
          source = self.packages.${system}.source;
        in {
          package = self.packages.${system}.default;
          prolog-library = pkgs.runCommand "a0-prolog-rlm-library" {
            nativeBuildInputs = [ pkgs.swi-prolog prologRlm ];
          } ''
            export HOME="$TMPDIR/home"
            mkdir -p "$HOME" "$TMPDIR/outside-source"
            cd "$TMPDIR/outside-source"
            swipl -q -g "use_module(library(rlm)),rlm:rlm_ready,halt"
            touch "$out"
          '';
          plugin-imports = pkgs.runCommand "a0-symbolic-plugin-imports" {
            nativeBuildInputs = [ python pkgs.swi-prolog prologRlm ];
          } ''
            export HOME="$TMPDIR/home"
            export PROLOG_RLM_ENABLED=1
            export SWIPL_PACK_PATH="${prologRlm}/share/swi-prolog/pack"
            mkdir -p "$HOME" "$TMPDIR/usr" "$TMPDIR/tmp"
            cd "${source}/share/a0-symbolics"
            ${python}/bin/python - <<'PY'
            from plugins._prolog_context_compiler.helpers.bridge import PrologContextBridge
            from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridge

            context = PrologContextBridge(timeout=10.0)
            try:
                compiled = context.compile({
                    "message": "return the result",
                    "max_context_tokens": 2048,
                    "units": [{
                        "format": "agent_zero_tool",
                        "kind": "tool",
                        "category": "agent",
                        "name": "response",
                        "description": "Return the final answer",
                        "content": "### response",
                        "schema": {"type": "object", "properties": {}},
                        "effect": "read",
                        "permanent": True,
                    }],
                })
                assert compiled["active_tools"] == ["response"]
            finally:
                context.close()

            runtime = PrologRuntimeBridge({"request_timeout_seconds": 10.0})
            try:
                status = runtime.call("status")
                assert status["ready"] is True
                catalog = runtime.call("tool_pack_catalog", {"declarations": [{
                    "format": "agent_zero_tool",
                    "kind": "tool",
                    "category": "process",
                    "name": "exec",
                    "description": "Execute source through Agent Zero",
                    "content": "### exec",
                    "schema": {
                        "type": "object",
                        "required": ["lang", "source_code"],
                        "additionalProperties": False,
                        "properties": {
                            "lang": {"type": "string"},
                            "source_code": {"type": "string"},
                        },
                    },
                    "effect": "process",
                    "permanent": True,
                }]})
                assert catalog["categories"] == ["process"]
                assert catalog["manifests"][0]["outcome"]["status"] == "loaded"
            finally:
                runtime.close()
            PY
            touch "$out"
          '';
        });
    };
}
