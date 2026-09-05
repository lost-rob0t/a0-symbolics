% Task-specific verification for the current worktree.
:- set_prolog_flag(unknown, error).
:- use_module(library(plunit)).
:- use_module(library(time)).
:- ensure_loaded('facts.kb').

current_successful_observation :-
    repo_state(Head, Digest),
    observation(_, _, exit(0), _, Head, Digest).

current_research_evidence :-
    research_required(false).
current_research_evidence :-
    research_required(true),
    repo_state(Head, Digest),
    brave_search(_, _, _, Head, Digest).

base_complete :-
    task(_),
    current_successful_observation,
    current_research_evidence.

% Extend this predicate with task-specific requirements and invariants.

% Task fix-broken-prs: every workflow action ref must either resolve on the
% data.forgejo.org mirror or be a fully-qualified https URL.
% observed fact shape from scans: workflow_ref(Branch, File, Ref).
complete :-
    base_complete,
    forall(workflow_ref(Branch, File, Ref),
           (atom_string(Ref, RefS),
            ( sub_atom(RefS, 0, _, _, 'https://')
            ; mirrored_action(RefS)
            ),
            format(user_error, "ok ~w ~w ~w~n", [Branch, File, RefS]))).

mirrored_action('actions/checkout@v4').
mirrored_action('actions/checkout@v5').
mirrored_action('actions/setup-java@v5').
mirrored_action('actions/upload-artifact@v4').
mirrored_action('docker/build-push-action@v6').
mirrored_action('docker/login-action@v3').
mirrored_action('docker/setup-buildx-action@v3').
mirrored_action('docker/setup-qemu-action@v3').

% The three refs known missing from data.forgejo.org must not remain anywhere.
no_broken_short_refs :-
    forall((workflow_ref(_, _, Ref), atom_string(Ref, RefS)),
           \+ member(RefS, [
               'android-actions/setup-android@v3',
               'gradle/actions/setup-gradle@v4',
               'cachix/install-nix-action@v31.11.1'])).

:- begin_tests(workspace_verification).

test(complete) :-
    complete.

test(no_broken_short_refs) :-
    no_broken_short_refs.

:- end_tests(workspace_verification).

main :-
    catch(call_with_time_limit(30, (run_tests, once(complete))),
          Error,
          (print_message(error, Error), fail)),
    !,
    halt(0).
main :-
    halt(1).

:- initialization(main, main).
