:- module(agent_zero_tool_pack,
          [ agent_zero_tool_pack_load/6
          ]).

/** <module> Agent Zero production tool-pack adapter

This module is shipped by Agent Zero, not by Prolog-RLM core.  It builds one
host-scoped external pack from the Agent Zero tools that are actually enabled
for an agent.  Prolog-RLM validates the inert manifest and schemas, while the
trusted host supplies the only executable handler closure.
*/

:- use_module(library(rlm_agent_zero_adapter)).
:- use_module(library(rlm_closed_data)).
:- use_module(library(rlm_tool_loader)).

:- meta_predicate agent_zero_tool_pack_load(+, +, +, +, 3, -).

agent_zero_tool_pack_load(Registry,
                          Pack,
                          Category,
                          Declarations,
                          HostHandler,
                          Outcome) :-
    closed_data_normalize(Declarations, CanonicalDeclarations),
    include(declaration_in_category(Category),
            CanonicalDeclarations,
            CategoryDeclarations),
    agent_zero_tool_pack_manifest(CategoryDeclarations,
                                  Category,
                                  ManifestOutcome),
    load_manifest_outcome(ManifestOutcome,
                          Registry,
                          Pack,
                          CategoryDeclarations,
                          HostHandler,
                          Outcome).

declaration_in_category(Category, Declaration) :-
    get_dict(category, Declaration, Declared0),
    ( atom(Declared0) -> Declared = Declared0
    ; string(Declared0) -> atom_string(Declared, Declared0)
    ),
    Declared == Category.

load_manifest_outcome(error(Error), _, _, _, _, error(Error)) :- !.
load_manifest_outcome(ok(Manifest), Registry, Pack, Declarations, HostHandler,
                      Outcome) :-
    Loader = agent_zero_tool_pack:load_declarations(Declarations, HostHandler),
    rlm_load_tool_pack_instance(Registry, Pack, Manifest, Loader, Outcome).

load_declarations(Declarations, HostHandler, Registry, Outcome) :-
    agent_zero_tool_registry_import(Registry,
                                    Declarations,
                                    HostHandler,
                                    Outcome).
