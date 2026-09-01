:- use_module(library(http/json)).
:- use_module(library(readutil)).

:- initialization(main, main).

main(Argv) :-
    load_runtime(Argv),
    request_loop.

load_runtime(Argv) :-
    (   append(_, ['--prolog-root', Root0|_], Argv)
    ->  atom_string(Root, Root0),
        directory_file_path(Root, prolog, PrologDirectory),
        asserta(user:file_search_path(library, PrologDirectory)),
        directory_file_path(Root, 'prolog/rlm.pl', Runtime),
        load_files(Runtime, [silent(true)])
    ;   use_module(library(rlm))
    ).

request_loop :-
    read_line_to_string(user_input, Line),
    (   Line == end_of_file
    ->  true
    ;   ( Line == "" -> true ; process_line(Line) ),
        request_loop
    ).

process_line(Line) :-
    catch(atom_json_dict(Line, Request, [value_string_as(string)]),
          Error,
          request_error("", Error)),
    (   is_dict(Request)
    ->  request_id(Request, RequestId),
        catch(process_request(RequestId, Request),
              Error,
              request_error(RequestId, Error))
    ;   true
    ).

process_request(RequestId, Request) :-
    require_action(Request, Action),
    request_arguments(Request, Arguments),
    dispatch(Action, Arguments, Result),
    json_safe(Result, Safe),
    write_reply(_{ok:true, request_id:RequestId, result:Safe}).

dispatch(status, _, Status) :-
    !,
    rlm:rlm_version(Version),
    Status = _{ready:true,
               version:Version,
               runtime:"prolog-rlm",
               policy_owner:"prolog",
               arbitrary_call:false,
               surfaces:[context_compiler,completion,recursive_query,
                         supervised_agents,plans,capabilities,authority,
                         durable_effects,graphs,artifacts,specs,mcp,
                         cancellation,tracing,usage,structured_outcomes,
                         direct,native_tools,spec_strategy,context_mounts]}.
dispatch(catalog, _, Catalog) :-
    !,
    Catalog = _{operations:[
        _{name:status, network:false},
        _{name:catalog, network:false},
        _{name:demo, network:false},
        _{name:context_compile, network:false},
        _{name:turn, network:true},
        _{name:direct, network:true},
        _{name:agent, network:true},
        _{name:complete, network:true}
    ]}.
dispatch(demo, Arguments, Outcome) :-
    !,
    required_text(Arguments, name, NameText),
    atom_string(Name, NameText),
    (   memberchk(Name, [context,tool,recursion,agent,graph,mcp])
    ->  rlm:demo(Name, Outcome)
    ;   throw(runtime_request_error(unsupported_demo(Name)))
    ).
dispatch(context_compile, Arguments, Outcome) :-
    !,
    required_dict(Arguments, request, CompileRequest),
    rlm:agent_zero_context_compile(CompileRequest, CompileOutcome),
    context_result(CompileOutcome, Outcome).
dispatch(turn, Arguments, Result) :-
    !,
    required_dict(Arguments, compile_request, CompileRequest),
    required_list(Arguments, messages, RecentMessages),
    required_list(Arguments, tools, DeclaredTools),
    required_text(Arguments, model, ModelText),
    atom_string(Model, ModelText),
    rlm:agent_zero_context_compile(CompileRequest, CompileOutcome),
    context_result(CompileOutcome, Projection),
    get_dict(active_tools, Projection, ActiveNames),
    active_provider_tools(DeclaredTools, ActiveNames, ActiveTools),
    get_dict(text, Projection, ContextText),
    projected_messages(ContextText, RecentMessages, Messages),
    turn_options(Arguments, ActiveTools, Options),
    Request = model_request{messages:Messages, options:Options},
    rlm_chain:openrouter_provider(Model, Provider0),
    auto_tool_choice_provider(Provider0, Provider),
    rlm_chain:model_complete(Provider, Request, ProviderOutcome),
    turn_result(ProviderOutcome, Projection, Result).
dispatch(direct, Arguments, Outcome) :-
    !,
    required_text(Arguments, prompt, Prompt),
    runtime_options(Arguments, Options),
    rlm:llm_query(Prompt, Options, Outcome).
dispatch(agent, Arguments, Outcome) :-
    !,
    required_text(Arguments, query, Query),
    optional_text(Arguments, context, "", Context),
    runtime_options(Arguments, Options),
    rlm:rlm_direct(Query, text(Context), Options, DirectOutcome),
    direct_result(DirectOutcome, Outcome).
dispatch(complete, Arguments, Outcome) :-
    !,
    required_text(Arguments, query, Query),
    optional_text(Arguments, context, "", Context),
    runtime_options(Arguments, Options),
    rlm:rlm_completion(Query, text(Context), Options, Outcome).
dispatch(Action, _, _) :-
    throw(runtime_request_error(unsupported_action(Action))).

active_provider_tools(Tools, ActiveNames0, ActiveTools) :-
    maplist(text_atom, ActiveNames0, ActiveNames),
    include(active_provider_tool(ActiveNames), Tools, Selected),
    maplist(provider_tool_wire, Selected, ActiveTools).

active_provider_tool(ActiveNames, Tool) :-
    is_dict(Tool),
    get_dict(function, Tool, Function),
    is_dict(Function),
    get_dict(name, Function, Name0),
    text_atom(Name0, Name),
    memberchk(Name, ActiveNames).

provider_tool_wire(Tool0, Tool) :-
    (   del_dict(original_name, Tool0, _, Tool1)
    ->  Tool = Tool1
    ;   Tool = Tool0
    ).

projected_messages(Context, RecentMessages,
                   [_{role:system, content:Context}|Messages]) :-
    maplist(provider_message, RecentMessages, Messages).

provider_message(Message0, Message) :-
    is_dict(Message0),
    get_dict(role, Message0, Role0),
    text_atom(Role0, Role),
    memberchk(Role, [system,user,assistant,tool]),
    get_dict(content, Message0, Content),
    ( string(Content) ; atom(Content) ; is_list(Content) ),
    put_dict(role, Message0, Role, Message).

turn_options(Arguments, Tools, Options) :-
    optional_positive_integer(Arguments, max_completion_tokens, 4096, MaxTokens),
    Base = _{max_completion_tokens:MaxTokens},
    (   Tools == []
    ->  Options = Base
    ;   put_dict(_{tools:Tools, tool_choice:"auto"}, Base, Options)
    ).

auto_tool_choice_provider(provider(Name, Config0),
                          provider(Name, [tool_choice_modes([auto])|Config0])).

turn_result(ok(Response), Projection, Result) :-
    !,
    put_dict(projection, Response, Projection, Result).
turn_result(error(Error), _, _) :-
    throw(runtime_request_error(provider_error(Error))).
turn_result(Outcome, _, _) :-
    throw(runtime_request_error(invalid_provider_outcome(Outcome))).

direct_result(ok(direct_result{value:Value,
                               usage:Usage,
                               turns:Turns,
                               iterations:Iterations,
                               tool_calls:ToolCalls,
                               context_calls:ContextCalls,
                               observation_bytes:ObservationBytes,
                               output_bytes:OutputBytes}),
              Result) :- !,
    Result = _{value:Value,
               usage:Usage,
               turns:Turns,
               iterations:Iterations,
               tool_calls:ToolCalls,
               context_calls:ContextCalls,
               observation_bytes:ObservationBytes,
               output_bytes:OutputBytes}.
direct_result(error(Error), _) :-
    throw(runtime_request_error(direct_error(Error))).
direct_result(Outcome, _) :-
    throw(runtime_request_error(invalid_direct_outcome(Outcome))).

context_result(ok(Projection), Projection) :- !.
context_result(error(Error), _) :-
    throw(runtime_request_error(context_compile_error(Error))).
context_result(Outcome, _) :-
    throw(runtime_request_error(invalid_context_outcome(Outcome))).

runtime_options(Arguments, [budget(Budget)]) :-
    rlm:default_completion_budget(Default),
    (   get_dict(budget, Arguments, Budget0)
    ->  must_be(dict, Budget0),
        put_dict(Budget0, Default, Budget)
    ;   Budget = Default
    ).

require_action(Request, Action) :-
    required_text(Request, action, Text),
    atom_string(Action, Text).

request_arguments(Request, Arguments) :-
    (   get_dict(arguments, Request, Arguments0)
    ->  must_be(dict, Arguments0), Arguments = Arguments0
    ;   Arguments = _{}
    ).

required_dict(Dict, Key, Value) :-
    get_dict(Key, Dict, Value),
    is_dict(Value),
    !.
required_dict(_, Key, _) :- throw(runtime_request_error(required_dict(Key))).

required_list(Dict, Key, Value) :-
    get_dict(Key, Dict, Value),
    is_list(Value),
    !.
required_list(_, Key, _) :- throw(runtime_request_error(required_list(Key))).

required_text(Dict, Key, Text) :-
    get_dict(Key, Dict, Value),
    worker_text_string(Value, Text),
    Text \== "",
    !.
required_text(_, Key, _) :- throw(runtime_request_error(required_text(Key))).

optional_text(Dict, Key, Default, Text) :-
    ( get_dict(Key, Dict, Value) -> worker_text_string(Value, Text) ; Text = Default ).

optional_positive_integer(Dict, Key, Default, Value) :-
    ( get_dict(Key, Dict, Value0) -> Value = Value0 ; Value = Default ),
    must_be(integer, Value),
    ( Value > 0 -> true ; throw(runtime_request_error(positive_integer(Key))) ).

request_id(Request, RequestId) :-
    ( get_dict(request_id, Request, Id0) -> worker_text_string(Id0, RequestId)
    ; RequestId = ""
    ).

request_error(RequestId, Error) :-
    message_to_string(Error, Message),
    term_string(Error, Detail, [quoted(true), numbervars(true)]),
    write_reply(_{ok:false, request_id:RequestId, error:Message, detail:Detail}).

write_reply(Reply) :-
    json_write_dict(current_output, Reply, [width(0)]),
    nl,
    flush_output.

text_atom(Value, Atom) :- atom(Value), !, Atom = Value.
text_atom(Value, Atom) :- string(Value), !, atom_string(Atom, Value).

worker_text_string(Value, Text) :- string(Value), !, Text = Value.
worker_text_string(Value, Text) :- atom(Value), !, atom_string(Value, Text).

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
