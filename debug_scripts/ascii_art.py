# /// script
# requires-python = ">=3.9"
# dependencies = ["python-escpos[usb]", "pyfiglet"]
# ///
from escpos.printer import Usb
from pyfiglet import Figlet

COLUMNS = 32


def render(text, font):
    lines = Figlet(font=font, width=1000).renderText(text).splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    width = max(map(len, lines))
    if width > COLUMNS:
        raise ValueError(f"{text!r} in {font} exceeds {COLUMNS} columns")
    padding = " " * ((COLUMNS - width) // 2)
    return "\n".join(padding + line.rstrip() for line in lines) + "\n"


receipts = [
    (f"{number} / {font}", render(number, font))
    for number, font in (("69", "standard"), ("420", "slant"), ("1337", "big"))
]
receipts += [
    (f"{word} / top to bottom", "\n".join(render(letter, "banner3") for letter in word))
    for word in ("LOL", "MOI", "JONO")
]

printer = Usb(0x0FE6, 0x811E, in_ep=0x82, out_ep=0x02)
try:
    printer.hw("INIT")
    printer.set(align="left", font="a", normal_textsize=True)
    for label, art in receipts:
        printer.text(f"{label}\n\n{art}\n")
        printer.cut()
        print(label, flush=True)
finally:
    printer.close()
