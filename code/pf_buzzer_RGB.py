import time
import Board

def beep(duration):
    Board.setBuzzer(1)
    time.sleep(duration)
    Board.setBuzzer(0)

def set_rgb(r, g, b):
    Board.RGB.setPixelColor(0, Board.PixelColor(r, g, b))
    Board.RGB.setPixelColor(1, Board.PixelColor(r, g, b))
    Board.RGB.show()

def flash_beep(r, g, b, duration, pause=0.05):
    set_rgb(r, g, b)
    beep(duration)
    set_rgb(0, 0, 0)
    time.sleep(pause)

def imperial_march():

    # Approximate rhythm and dramatic timing
    short = 0.3
    med = 0.4
    long = 0.6

    red = (255, 0, 0)
    blue = (0, 0, 255)

    try:
        # Opening: DUN DUN DUN, dun DUN DUN
        flash_beep(*red, short)
        time.sleep(0.05)
        flash_beep(*red, short)
        time.sleep(0.05)
        flash_beep(*red, short)
        time.sleep(0.3)

        flash_beep(*blue, med)
        time.sleep(0.1)
        flash_beep(*red, short)
        time.sleep(0.05)
        flash_beep(*red, long)

        time.sleep(0.3)

        # Repeat with variation
        flash_beep(*blue, short)
        time.sleep(0.05)
        flash_beep(*blue, short)
        time.sleep(0.05)
        flash_beep(*blue, short)
        time.sleep(0.3)

        flash_beep(*red, med)
        time.sleep(0.1)
        flash_beep(*blue, short)
        time.sleep(0.05)
        flash_beep(*red, long)

        # End with fade to green
        set_rgb(0, 255, 0)
        time.sleep(1)

    finally:
        Board.setBuzzer(0)
        set_rgb(0, 0, 0)


if __name__ == "__main__":
    imperial_march()

