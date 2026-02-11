# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "python-escpos[usb]",
# ]
# ///
from escpos.printer import Usb, Dummy

PRINTER_VENDOR_ID = 0x0fe6
PRINTER_PRODUCT_ID = 0x811e      

# --- HARDWARE SETUP: PRINTER ---
try:
    p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID,  in_ep=0x82, out_ep=0x02)
except Exception:
    print("⚠️ Printer not found. Using Dummy mode.")
    p = Dummy()

def print_ticket(number=67):
    try:
        p.text("\n")
        p.set(align='center')
        p.text("VUORONUMERO\n")
        p.text("----------------\n")
        p.set(align='center', width=4, height=4) 
        p.text(f"{number}\n")
        p.set(align='center', width=1, height=1)
        p.cut()
    except Exception as e:
        print(f"❌ Print Error: {e}")

print_ticket()
