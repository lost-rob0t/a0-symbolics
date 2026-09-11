:- module(agent_zero_host_tools,
          [ host_tool_options/4,
            cleanup_host_tools/1,
            host_tool_bridge/4,
            json_safe/2
          ]).

/** <module> Agent Zero trusted host-tool bridge for the runtime worker

This module is shipped by Agent Zero, not by Prolog-RLM core.  The runtime
owns tool management: the host sends the Agent Zero tool declarations it
collected through the context compiler, this module validates the inert
manifest and schemas into a tool registry, and the provider's native tool
calls round-trip to the trusted host through callback frames.

Authority for the registry's own context is delegated to ``allow_session``
because Agent Zero remains the execution-policy authority (scoped tool
policy, intervention handling, and plugin hooks run on the host side), and
the bridge frames carry only the tool call, never credentials.
*/

:- use_module(library(rlm_tool)).
:- use_module(library(rlm_authority)).
:- use_module(library(adaptors/rlm_agent_zero_adapter)).

host_tool_options(Arguments, Options0, Options, Registry) :-
    (   get_dict(declarations, Arguments, Declarations0),
        is_list(Declarations0),
        Declarations0 \== [],
        get_dict(session, Arguments, Session0),
        text_string(Session0, Session)
    ->  rlm_tool:tool_registry_create(Registry),
        catch(host_tool_registry_setup(Registry, Declarations0, Session,
                                       Capabilities),
              Error,
              ( cleanup_host_tools(Registry), throw(Error) )),
        Options = [tool_registry(Registry), capabilities(Capabilities)|Options0]
    ;   Options = Options0,
        Registry = none
    ).

host_tool_registry_setup(Registry, Declarations, Session, Capabilities) :-
    rlm_agent_zero_adapter:agent_zero_tool_registry_import(
        Registry, Declarations, host_tool_bridge(Session), ImportOutcome),
    (   ImportOutcome = ok(Import)
    ->  true
    ;   ImportOutcome = error(Cause)
    ->  throw(runtime_request_error(tool_registry_import_rejected(Cause)))
    ;   throw(runtime_request_error(tool_registry_import_invalid_outcome))
    ),
    Registry = tool_registry(Id),
    rlm_authority:rlm_set_authority(tool_registry(Id), allow_session, _),
    registry_capabilities(Import.schemas, Capabilities).

text_string(Value, Text) :- string(Value), !, Text = Value.
text_string(Value, Text) :- atom(Value), !, atom_string(Value, Text).

registry_capabilities(Schemas, Capabilities) :-
    findall(Capability,
            ( member(Schema, Schemas),
              get_dict(capability, Schema, Capability) ),
            Capabilities0),
    sort(Capabilities0, Capabilities).

cleanup_host_tools(none) :- !.
cleanup_host_tools(Registry) :-
    (   Registry = tool_registry(Id)
    ->  catch(rlm_authority:rlm_authority_clear(tool_registry(Id)), _, true)
    ;   true
    ),
    catch(rlm_tool:tool_registry_destroy(Registry), _, true).

:- dynamic host_call_counter/1.
host_call_counter(0).

next_host_call_id(Id) :-
    (   retract(host_call_counter(N)) -> true ; N = 0 ),
    M is N + 1,
    asserta(host_call_counter(M)),
    format(atom(Id), "call-~d", [M]).

% Trusted host tool bridge: called by the registry when the provider selects
% a declared Agent Zero tool. Emits one callback frame and blocks for the
% host's inline reply; the worker is single-threaded, so the framing is safe.
host_tool_bridge(Session, Name, Args, Result) :-
    (   atom(Name) -> atom_string(Name, NameText) ; NameText = Name ),
    json_safe(Args, SafeArgs),
    next_host_call_id(CallId),
    json_write_dict(current_output,
                    _{callback:"tool",
                      call_id:CallId,
                      token:Session,
                      name:NameText,
                      arguments:SafeArgs},
                    [width(0)]),
    nl,
    flush_output,
    read_line_to_string(user_input, Line),
    (   Line == end_of_file
    ->  throw(runtime_request_error(host_tool_bridge_closed))
    ;   catch(atom_json_dict(Line, Reply, [value_string_as(string)]),
              _,
              throw(runtime_request_error(host_tool_bridge_reply_malformed)))
    ),
    (   is_dict(Reply),
        Reply.get(call_id) == CallId,
        Reply.get(ok) == true,
        is_dict(Reply.get(result))
    ->  Result = Reply.get(result)
    ;   is_dict(Reply),
        Reply.get(call_id) == CallId,
        Reply.get(ok) == false
    ->  json_safe(Reply.get(error), SafeError),
        throw(runtime_request_error(host_tool_execution_failed(SafeError)))
    ;   throw(runtime_request_error(host_tool_bridge_reply_invalid))
    ).
% Shared JSON-safe projection for protocol frames (mirrors the worker's
% renderer): atoms and compounds become strings / $term wrappers.
json_safe(Value, Safe) :-
    (   var(Value)
    ->  Safe = "_"
    ;   is_dict(Value)
    ->  dict_pairs(Value, _, Pairs),
        maplist(json_pair, Pairs, SafePairs),
        dict_pairs(Safe, json, SafePairs)
    ;   is_list(Value)
    ->  maplist(json_safe, Value, Safe)
    ;   string(Value)
    ->  Safe = Value
    ;   number(Value)
    ->  Safe = Value
    ;   memberchk(Value, [true,false,null])
    ->  Safe = Value
    ;   atom(Value)
    ->  atom_string(Value, Safe)
    ;   compound(Value)
    ->  Value =.. [Functor|Args],
        atom_string(Functor, FunctorText),
        maplist(json_safe, Args, SafeArgs),
        Safe = _{'$term':FunctorText, args:SafeArgs}
    ;   term_string(Value, Safe, [quoted(true), numbervars(true)])
    ).

json_pair(Key-Value, Key-Safe) :- json_safe(Value, Safe).
