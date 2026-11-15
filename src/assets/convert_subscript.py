r"""Convert brace-delimited AutoKey input to Unicode subscripts or superscripts.

The abbreviations ``\_{`` and ``\^{`` select subscript and superscript conversion,
respectively. For example, ``\_{123}`` becomes ``₁₂₃`` and ``\^{Ab2}`` becomes
``ᴬᵇ²``. Conversion requires a closing brace and a mapping for every enclosed
character; incomplete or unsupported input is left unchanged.

AutoKey must inject the ``keyboard`` and ``engine`` globals before executing this
script. The script calls ``main()`` immediately when executed or imported.

Attributes:
    SUBSCRIPTS: Character-to-subscript mapping. None marks unsupported characters.
    SUPERSCRIPTS: Character-to-superscript mapping. None marks unsupported
        characters.
    MAX_CHARS: Maximum buffer length before key-event collection stops. The
        closing brace counts toward this length.
    TIMEOUT: Maximum time in seconds to wait for key events.
    TRIGGER: Mapping from AutoKey abbreviations to their conversion mappings.
"""

from functools import partial

from autokey.model.key import Key
from autokey.scripting import Engine, Keyboard

SUBSCRIPTS: dict[str, str | None] = {
    "0": r"₀", "1": r"₁", "2": r"₂", "3": r"₃", "4": r"₄",
    "5": r"₅", "6": r"₆", "7": r"₇", "8": r"₈", "9": r"₉",
    "+": r"₊", "-": r"₋", "=": r"₌", "(": r"₍", ")": r"₎",
    # lowercase letters
    "a": r"ₐ", "b": None, "c": None, "d": None, "e": r"ₑ",
    "f": None, "g": None, "h": r"ₕ", "i": r"ᵢ", "j": r"ⱼ",
    "k": r"ₖ", "l": r"ₗ", "m": r"ₘ", "n": r"ₙ", "o": r"ₒ",
    "p": r"ₚ", "q": None, "r": r"ᵣ", "s": r"ₛ", "t": r"ₜ",
    "u": r"ᵤ", "v": r"ᵥ", "w": r"₝", "x": r"ₓ", "y": r"₞",
    "z": r"₟",
}  # fmt: skip

SUPERSCRIPTS: dict[str, str | None] = {
    "0": r"⁰", "1": r"¹", "2": r"²", "3": r"³", "4": r"⁴",
    "5": r"⁵", "6": r"⁶", "7": r"⁷", "8": r"⁸", "9": r"⁹",
    "+": r"⁺", "-": r"⁻", "=": r"⁼", "(": r"⁽", ")": r"⁾",
    # lowercase letters
    "a": r"ᵃ", "b": r"ᵇ", "c": r"ᶜ", "d": r"ᵈ", "e": r"ᵉ",
    "f": r"ᶠ", "g": r"ᵍ", "h": r"ʰ", "i": r"ⁱ", "j": r"ʲ",
    "k": r"ᵏ", "l": r"ˡ", "m": r"ᵐ", "n": r"ⁿ", "o": r"ᵒ",
    "p": r"ᵖ", "q": r"𐞥", "r": r"ʳ", "s": r"ˢ", "t": r"ᵗ",
    "u": r"ᵘ", "v": r"ᵛ", "w": r"ʷ", "x": r"ˣ", "y": r"ʸ",
    "z": r"ᶻ",
    # uppercase letters
    "A": r"ᴬ", "B": r"ᴮ", "C": r"ꟲ", "D": r"ᴰ", "E": r"ᴱ",
    "F": r"ꟳ", "G": r"ᴳ", "H": r"ᴴ", "I": r"ᴵ", "J": r"ᴶ",
    "K": r"ᴷ", "L": r"ᴸ", "M": r"ᴹ", "N": r"ᴺ", "O": r"ᴼ",
    "P": r"ᴾ", "Q": r"ꟴ", "R": r"ᴿ", "S": r"꟱", "T": r"ᵀ",
    "U": r"ᵁ", "V": r"ⱽ", "W": r"ᵂ", "X": None, "Y": None,
    "Z": None,
}  # fmt: skip

MAX_CHARS = 10
TIMEOUT = 10.0
TRIGGER = {
    r"\_{": SUBSCRIPTS,
    r"\^{": SUPERSCRIPTS,
}


def check_keyevent(waiter, raw_key, modifiers, key, *args, chars: list[str]) -> bool:
    """Update the input buffer and decide whether to stop collecting key events.

    Backspace removes the last buffered character, or stops collection if the
    buffer is empty. Other special keys and modifiers other than Shift or AltGr
    stop collection. Ordinary key values are appended to the buffer, including
    the terminating closing brace.

    Args:
        waiter: AutoKey waiter supplied to the callback; unused.
        raw_key: Raw key value supplied by AutoKey; unused.
        modifiers: Active key modifiers for the event.
        key: Key value to process, including AutoKey special-key identifiers.
        *args: Additional positional callback arguments; unused.
        chars: Mutable buffer of collected characters, updated in place.

    Returns:
        True to stop collection when a closing brace is received, the buffer
        length exceeds MAX_CHARS, or an interrupting key event occurs. False to
        continue collecting key events.
    """
    if key == Key.BACKSPACE:
        if chars:
            chars.pop()
            return False
        return True

    if Key.is_key(key) or not set(modifiers) <= {Key.SHIFT, Key.ALT_GR}:
        return True

    chars.append(key)
    return key == "}" or len(chars) > MAX_CHARS


def main() -> None:
    """Convert input following the triggered AutoKey abbreviation.

    Obtain the conversion mapping from the triggered abbreviation and collect
    key events for up to TIMEOUT seconds. If the buffer ends with a closing
    brace and every preceding character has a replacement, erase the abbreviation
    and collected input, then type the converted text. Otherwise, leave the
    typed text unchanged. An empty brace pair removes only the abbreviation and
    closing brace.

    The ``keyboard`` and ``engine`` objects must be provided as module globals
    by AutoKey.

    Raises:
        RuntimeError: If either required AutoKey global is missing or None.
        AssertionError: If AutoKey reports no triggered abbreviation.
        ValueError: If the triggered abbreviation is not present in TRIGGER.
    """
    keyboard: Keyboard | None = globals().get("keyboard")
    engine: Engine | None = globals().get("engine")
    if keyboard is None or engine is None:
        raise RuntimeError("Expected keyboard and engine globals injected by autokey.")

    abbreviation, _ = engine.get_triggered_abbreviation()
    assert abbreviation is not None, "Expected a triggered abbreviation"
    mapping = TRIGGER.get(abbreviation)

    if mapping is None:
        raise ValueError(f"Expected one of {TRIGGER.keys()}, got {abbreviation!r}")

    chars: list[str] = []  # mutated by wait_for_keyevent
    keyboard.wait_for_keyevent(
        partial(check_keyevent, chars=chars),
        name="unicode-sub-super-script",
        timeOut=TIMEOUT,
    )

    if not chars or chars.pop() != "}":
        # TIMEOUT reached or MAX_CHARS exceeded
        return

    replacements: list[str | None] = [mapping.get(char) for char in chars]

    if all(replacements):  # no None or empty strings
        keyboard.send_key(
            Key.BACKSPACE,
            repeat=len(abbreviation) + len(chars) + 1,
        )
        keyboard.send_keys("".join(replacements))  # type: ignore


main()
