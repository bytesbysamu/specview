# flask/modules/ai/tests/test_prompts.py
from modules.ai import prompts as _prompts

# Aliases with no underscores avoid pytest collection under python_functions=["test_*", "*_*"]
generatePrompt = _prompts.generate_prompt
generateSpecPrompt = _prompts.generate_spec_prompt
iteratePrompt = _prompts.iterate_prompt
lintBraindumpPrompt = _prompts.lint_braindump_prompt
reviewPrompt = _prompts.review_prompt
rewritePrompt = _prompts.rewrite_prompt
scanPrompt = _prompts.scan_prompt


def rewritePrompt_embedsTextAndInstructions():
    _, prompt = rewritePrompt("Hello world", "Make it formal")
    assert "Hello world" in prompt
    assert "Make it formal" in prompt


def rewritePrompt_systemHasNoBuilderContext():
    system, _ = rewritePrompt("x", "y")
    assert "Builder" not in system
    assert "Principles" not in system


def generatePrompt_embedsBuilderInSystem():
    system, _ = generatePrompt("write a spec", "I am a solo founder", "", "")
    assert "I am a solo founder" in system


def generatePrompt_omitsBuilderSectionWhenEmpty():
    system, _ = generatePrompt("write a spec", "", "", "")
    assert "Builder Profile" not in system


def generatePrompt_embedsToneInSystem():
    system, _ = generatePrompt("write a spec", "", "", "concise")
    assert "concise" in system


def iteratePrompt_embedsBaseSpec():
    _, prompt = iteratePrompt("base spec content", "current doc", "", "")
    assert "base spec content" in prompt


def iteratePrompt_embedsCurrentContent():
    _, prompt = iteratePrompt("base", "current doc content", "", "")
    assert "current doc content" in prompt


def iteratePrompt_embedsPrinciplesInSystem():
    system, _ = iteratePrompt("base", "current", "", "ship fast, validate first")
    assert "ship fast, validate first" in system


def generateSpecPrompt_containsFileMarkerInstruction():
    system, _ = generateSpecPrompt("my product idea", "", "")
    assert "===FILE:" in system


def generateSpecPrompt_embedsPrinciples():
    system, _ = generateSpecPrompt("my product idea", "", "minimal, ship fast")
    assert "minimal, ship fast" in system


def reviewPrompt_systemContainsAllSixDimensions():
    system, _ = reviewPrompt({"spec.md": "content"})
    for dimension in ("clarity", "completeness", "actionability", "consistency",
                      "specificity", "feasibility"):
        assert dimension in system, f"review_prompt system missing dimension: {dimension}"


def reviewPrompt_requestsJsonOutput():
    system, _ = reviewPrompt({})
    assert "JSON" in system


def lintBraindumpPrompt_embedsBraindump():
    _, prompt = lintBraindumpPrompt("my product idea text")
    assert "my product idea text" in prompt


def lintBraindumpPrompt_requestsJsonOutput():
    system, _ = lintBraindumpPrompt("")
    assert "JSON" in system


def scanPrompt_embedsTreeText():
    _, prompt = scanPrompt("src/\n  main.py")
    assert "src/" in prompt
    assert "main.py" in prompt


def scanPrompt_systemProhibitsWriteOperations():
    system, _ = scanPrompt("")
    # Claude CLI converts write intent into a tool-use permission stub;
    # the scan system prompt must explicitly forbid it.
    assert "Do NOT" in system, (
        "scan_prompt system must explicitly prohibit write operations — "
        "Claude CLI converts write intent into a permission stub (see architecture.md)"
    )
