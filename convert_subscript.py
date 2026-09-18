from functools import partial

from autokey.model.key import Key  # type: ignore
from autokey.scripting import Engine, Keyboard  # type: ignore

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
    keyboard: Keyboard | None = globals().get("keyboard")
    engine: Engine | None = globals().get("engine")
    if keyboard is None or engine is None:
        raise RuntimeError("Expected keyboard and engine globals injected by autokey.")

    abbreviation, _ = engine.get_triggered_abbreviation()
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
