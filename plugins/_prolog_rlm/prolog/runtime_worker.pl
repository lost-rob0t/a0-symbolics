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
    ),
    load_agent_zero_pack.

load_agent_zero_pack :-
    source_file(main(_), Worker),
    file_directory_name(Worker, Directory),
    directory_file_path(Directory, 'agent_zero_tool_pack.pl', Pack),
    load_files(Pack, [silent(true)]).

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
                         cancellation,tracing,usage,structured_outcomes]}.
dispatch(catalog, _, Catalog) :-
    !,
    Catalog = _{operations:[
        _{name:status, network:false},
        _{name:catalog, network:false},
        _{name:demo, network:false},
        _{name:context_compile, network:false},
        _{name:tool_pack_catalog, network:false},
        _{name:direct, network:true},
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
    rlm:agent_zero_context_compile(CompileRequest, Outcome).
dispatch(tool_pack_catalog, Arguments, Catalog) :-
    !,
    required_list(Arguments, declarations, Declarations),
    declaration_categories(Declarations, Categories),
    maplist(pack_manifest(Declarations), Categories, Manifests),
    Catalog = _{categories:Categories, manifests:Manifests}.
dispatch(direct, Arguments, Outcome) :-
    !,
    required_text(Arguments, prompt, Prompt),
    runtime_options(Arguments, Options),
    rlm:llm_query(Prompt, Options, Outcome).
dispatch(complete, Arguments, Outcome) :-
    !,
    required_text(Arguments, query, Query),
    optional_text(Arguments, context, "", Context),
    runtime_options(Arguments, Options0),
    context_bytes_option(Arguments, Options0, Options),
    rlm:rlm_completion(Query, text(Context), Options, Outcome).
dispatch(Action, _, _) :-
    throw(runtime_request_error(unsupported_action(Action))).

context_bytes_option(Arguments, Options0, [context_bytes(Bytes)|Options0]) :-
    get_dict(context_bytes, Arguments, Bytes0),
    integer(Bytes0),
    Bytes0 > 0,
    !,
    Bytes = Bytes0.
context_bytes_option(_, Options, Options).

pack_manifest(Declarations, Category, Manifest) :-
    atomic_list_concat([agent_zero, Category], '_', Pack),
    setup_call_cleanup(
        rlm_tool:tool_registry_create(Registry),
        ( agent_zero_tool_pack:agent_zero_tool_pack_load(
              Registry,
              Pack,
              Category,
              Declarations,
              user:inert_host_tool,
              LoadOutcome),
          pack_load_result(LoadOutcome, Outcome),
          rlm_tool:tool_discover(Registry, Schemas),
          Manifest = _{category:Category,
                       outcome:Outcome,
                       schemas:Schemas}
        ),
        rlm_tool:tool_registry_destroy(Registry)).

pack_load_result(ok(Loaded), Loaded) :- !.
pack_load_result(error(Error), _{status:error, error:Error}) :- !.
pack_load_result(Other, _{status:error, error:Other}).

inert_host_tool(_, _, _) :-
    throw(runtime_request_error(host_tool_execution_not_available)).

declaration_categories(Declarations, Categories) :-
    findall(Category,
            ( member(Declaration, Declarations),
              is_dict(Declaration),
              get_dict(category, Declaration, Category0),
              text_atom(Category0, Category) ),
            Categories0),
    sort(Categories0, Categories).

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
    text_string(Value, Text),
    Text \== "",
    !.
required_text(_, Key, _) :- throw(runtime_request_error(required_text(Key))).

optional_text(Dict, Key, Default, Text) :-
    ( get_dict(Key, Dict, Value) -> text_string(Value, Text) ; Text = Default ).

request_id(Request, RequestId) :-
    ( get_dict(request_id, Request, Id0) -> text_string(Id0, RequestId)
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

text_string(Value, Text) :- string(Value), !, Text = Value.
text_string(Value, Text) :- atom(Value), !, atom_string(Value, Text).

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
