"""Router: command-line / ops requests classify as `coding`.

Guards the enhancement that terminal/how-to/install requests come from the
coding model (and inherit copy-paste command formatting) — while genuine
concept questions ("how does X work") stay `complex`.
"""
from src.model_router import classify_heuristic


def _cat(msg: str) -> str:
    return classify_heuristic(msg)[0]


def test_terminal_command_request_is_coding():
    # The exact shape that used to be answered by the complex model as prose.
    assert _cat("Give me a code block I can enter into my terminal to mount "
                "this drive and connect it to the cookbook") == "coding"


def test_how_do_i_install_is_coding():
    assert _cat("how do I install docker on ubuntu") == "coding"


def test_command_to_restart_service_is_coding():
    assert _cat("what command do I use to restart the ollama service") == "coding"


def test_one_liner_request_is_coding():
    assert _cat("give me a one-liner to find the largest files") == "coding"


def test_ops_verb_with_tool_is_coding():
    assert _cat("mount the external drive via fstab") == "coding"
    assert _cat("systemctl enable my service") == "coding"


def test_classic_coding_still_coding():
    assert _cat("write a python function to parse a csv") == "coding"


def test_concept_how_does_stays_complex():
    # "how does X work" is explanation, not a task — must not be dragged to coding.
    assert _cat("how does photosynthesis work") == "complex"
    assert _cat("explain the theory of relativity in detail") == "complex"


def test_trivia_stays_simple():
    assert _cat("what is the capital of France") == "simple"


def test_weak_single_ops_word_not_forced_high_coding():
    # A lone ops-ish word in a non-technical sentence must not be forced to
    # high-confidence coding; it falls to the low-confidence tie-breaker.
    cat, conf = classify_heuristic("restart my meditation habit tips")
    assert not (cat == "coding" and conf == "high")
