:- begin_tests(agent_zero_tool_pack).

:- use_module(library(rlm_tool)).
:- use_module(library(rlm_authority)).
:- use_module('../prolog/agent_zero_tool_pack').
:- use_module(library(adaptors/rlm_agent_zero_adapter)).
:- use_module('../prolog/agent_zero_host_tools').

declarations([
    _{format:agent_zero_tool,
      kind:tool,
      category:agent,
      name:response,
      description:"Return the final answer",
      content:"### response",
      schema:_{type:"object", properties:_{text:_{type:"string"}}},
      effect:read,
      permanent:true},
    _{format:agent_zero_tool,
      kind:tool,
      category:filesystem,
      name:text_editor,
      description:"Read and edit files",
      content:"### text_editor",
      schema:_{type:"object", properties:_{path:_{type:"string"}}},
      effect:write,
      permanent:true},
    _{format:agent_zero_tool,
      kind:tool,
      category:process,
      name:exec,
      description:"Execute source through the Agent Zero runtime",
      content:"### exec",
      schema:_{type:"object",
               required:[lang,source_code],
               additionalProperties:false,
               properties:_{lang:_{type:"string"},
                            source_code:_{type:"string"}}},
      effect:process,
      permanent:true},
    _{format:agent_zero_tool,
      kind:tool,
      category:git,
      name:git,
      description:"Inspect Git state and diffs",
      content:"### git",
      schema:_{type:"object",
               required:[action],
               additionalProperties:false,
               properties:_{action:_{type:"string"}}},
      effect:read,
      permanent:true},
    _{format:agent_zero_tool,
      kind:tool,
      category:filesystem,
      name:patch,
      description:"Apply a stale-safe text patch",
      content:"### patch",
      schema:_{type:"object",
               required:[path],
               additionalProperties:false,
               properties:_{path:_{type:"string"}}},
      effect:write,
      permanent:true}
]).

test(loads_only_requested_production_category_and_invokes_trusted_host) :-
    declarations(Declarations),
    setup_call_cleanup(
        tool_registry_create(Registry),
        ( agent_zero_tool_pack_load(
              Registry,
              agent_zero_agent_tools,
              agent,
              Declarations,
              plunit_agent_zero_tool_pack:host_tool,
              ok(Loaded)),
          assertion(Loaded.status == loaded),
          tool_lookup(Registry, response, ok(_)),
          tool_lookup(Registry, text_editor, error(Missing)),
          assertion(Missing.kind == unknown_tool),
          tool_invoke(Registry,
                      [tool(response)],
                      response,
                      _{text:"done"},
                      [],
                      ok(Execution),
                      Trace),
          assertion(Execution.value.tool == response),
          assertion(Execution.value.args.text == "done"),
          assertion(Trace.authorization == allowed)
        ),
        tool_registry_destroy(Registry)).

test(pack_manifest_cannot_grant_capability) :-
    declarations(Declarations),
    setup_call_cleanup(
        tool_registry_create(Registry),
        ( agent_zero_tool_pack_load(
              Registry,
              agent_zero_agent_tools,
              agent,
              Declarations,
              plunit_agent_zero_tool_pack:host_tool,
              ok(_)),
          tool_invoke(Registry,
                      [],
                      response,
                      _{text:"done"},
                      [],
                      error(Error),
                      Trace),
          assertion(Error.kind == capability_denied),
          assertion(Trace.authorization == denied)
        ),
        tool_registry_destroy(Registry)).

test(production_pack_loads_exec_git_and_patch_as_separate_categories) :-
    declarations(Declarations),
    forall(
        member(Category-Name,
               [process-exec, git-git, filesystem-patch]),
        setup_call_cleanup(
            tool_registry_create(Registry),
            ( agent_zero_tool_pack_load(
                  Registry,
                  agent_zero_production_tools,
                  Category,
                  Declarations,
                  plunit_agent_zero_tool_pack:host_tool,
                  ok(Loaded)),
              assertion(Loaded.status == loaded),
              tool_lookup(Registry, Name, ok(Schema)),
              assertion(Schema.name == Name)
            ),
            tool_registry_destroy(Registry))).

host_tool(Name, Args, _{tool:Name, args:Args}).

% The worker's host_tool_options wiring (registry + capabilities + authority)
% is validated structurally; the bridge's IPC framing is exercised by the
% Python transport test, and effectful tools by the live direct-mode smoke.
test(host_tool_options_builds_registry_capabilities_and_authority) :-
    declarations(Declarations),
    Session = "session-token",
    Request = _{prompt:"p", context:"", declarations:Declarations, session:Session},
    agent_zero_host_tools:host_tool_options(Request, [budget(_{})], Options, Registry),
    assertion(Options = [tool_registry(Registry), capabilities(Caps), budget(_Base)]),
    Registry = tool_registry(Id),
    assertion(memberchk(tool(response), Caps)),
    assertion(memberchk(tool(text_editor), Caps)),
    assertion(memberchk(tool(exec), Caps)),
    assertion(memberchk(tool(git), Caps)),
    assertion(memberchk(tool(patch), Caps)),
    ( rlm_authority:rlm_authority_clear(tool_registry(Id)) -> true ; true ),
    tool_registry_destroy(Registry),
    !.

test(host_tool_options_without_declarations_stays_tool_less) :-
    agent_zero_host_tools:host_tool_options(
        _{prompt:"p"}, [budget(_{})], Options, none),
    assertion(Options = [budget(_Base)]),
    assertion(length(Options, 1)).

test(duplicate_declaration_names_fail_closed) :-
    Declarations = [
        _{format:agent_zero_tool, kind:tool, category:agent,
          name:dup, description:"one", content:"### one",
          schema:_{}, effect:read, permanent:false},
        _{format:agent_zero_tool, kind:tool, category:filesystem,
          name:dup, description:"two", content:"### two",
          schema:_{}, effect:read, permanent:false}
    ],
    setup_call_cleanup(
        tool_registry_create(Registry),
        ( rlm_agent_zero_adapter:agent_zero_tool_registry_import(
              Registry, Declarations,
              plunit_agent_zero_tool_pack:host_tool,
              error(AdapterError)),
          assertion(AdapterError.kind == invalid_agent_zero_context),
          AdapterError.detail = dependency_error(ToolError),
          assertion(ToolError.kind == duplicate_tool),
          assertion(ToolError.tool == dup)
        ),
        tool_registry_destroy(Registry)).

:- end_tests(agent_zero_tool_pack).
