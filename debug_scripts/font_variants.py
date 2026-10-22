# /// script
# requires-python = ">=3.9"
# dependencies = ["python-escpos[usb]"]
# ///
from escpos.printer import Usb

printer = Usb(0x0FE6, 0x811E, in_ep=0x82, out_ep=0x02)
try:
    printer.hw("INIT")
    for font in ("a", "b"):
        for scale in (3, 4, 6, 8):
            label = f"Font {font.upper()} - {scale}x width, {scale}x height"
            printer.set(align="center", font="a", normal_textsize=True)
            printer.text(f"{label}\nVUORONUMERO\n\n")
            printer.set(font=font, custom_size=True, width=scale, height=scale)
            printer.text("67\n")
            printer.set(normal_textsize=True)
            printer.cut()
            print(label, flush=True)
finally:
    printer.close()
