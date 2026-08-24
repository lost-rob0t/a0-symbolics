:- use_module(library(http/json)).
:- use_module(library(readutil)).

:- initialization(main, main).

main(Argv) :-
    load_agent_zero_adapter(Argv),
    request_loop.

load_agent_zero_adapter(Argv) :-
    (   append(_, ['--prolog-root', Root0|_], Argv)
    ->  atom_string(Root, Root0),
        directory_file_path(Root, 'prolog/rlm_agent_zero_adapter.pl', Adapter),
        load_files(Adapter, [silent(true)])
    ;   use_module(library(rlm_agent_zero_adapter))
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
    rlm_agent_zero_adapter:agent_zero_context_compile(Request, Outcome),
    reply_outcome(Outcome, RequestId).

reply_outcome(ok(Result), RequestId) :-
    !,
    maplist(unit_id, Result.active_units, ActiveUnits),
    maplist(atom_string, Result.active_tools, ActiveTools),
    json_safe(Result.token_ledger, TokenLedger),
    json_safe(Result.rejected, Rejected),
    Reply = _{ok:true,
              request_id:RequestId,
              text:Result.text,
              active_units:ActiveUnits,
              active_tools:ActiveTools,
              fingerprint:Result.fingerprint,
              token_ledger:TokenLedger,
              rejected:Rejected,
              warnings:Result.warnings},
    write_reply(Reply).
reply_outcome(error(Error), RequestId) :-
    json_safe(Error, Safe),
    write_reply(_{ok:false,
                  request_id:RequestId,
                  error:"Prolog-RLM rejected Agent Zero context metadata",
                  detail:Safe}).

request_id(Request, RequestId) :-
    ( get_dict(request_id, Request, Id0) -> text_string(Id0, RequestId)
    ; RequestId = ""
    ).

request_error(RequestId, Error) :-
    message_to_string(Error, Message),
    write_reply(_{ok:false, request_id:RequestId, error:Message}).

write_reply(Reply) :-
    json_write_dict(current_output, Reply, [width(0)]),
    nl,
    flush_output.

unit_id(tool(Name), Text) :- format(string(Text), "tool:~w", [Name]).
unit_id(instruction(Name), Text) :- format(string(Text), "instruction:~w", [Name]).
unit_id(skill(Name), Text) :- format(string(Text), "skill:~w", [Name]).
unit_id(resource(Name), Text) :- format(string(Text), "resource:~w", [Name]).
unit_id(mcp_tool(Server, Name), Text) :-
    format(string(Text), "mcp_tool:~w:~w", [Server, Name]).
unit_id(Unit, Text) :- term_string(Unit, Text, [quoted(true)]).

text_string(Value, Text) :- string(Value), !, Text = Value.
text_string(Value, Text) :- atom(Value), !, atom_string(Value, Text).
text_string(Value, Text) :- term_string(Value, Text, [quoted(true)]).

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
    ;   Value == true
    ->  Safe = true
    ;   Value == false
    ->  Safe = false
    ;   Value == null
    ->  Safe = null
    ;   atom(Value)
    ->  atom_string(Value, Safe)
    ;   term_string(Value, Safe, [quoted(true), numbervars(true)])
    ).

json_pair(Key-Value, Key-Safe) :- json_safe(Value, Safe).
