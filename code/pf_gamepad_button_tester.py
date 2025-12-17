#!/usr/bin/env python
import time
import pygame

# How often to print a full snapshot of axes/buttons (seconds)
SNAPSHOT_EVERY_SEC = 1.0

def snapshot(js: pygame.joystick.Joystick) -> None:
    axes = [round(js.get_axis(i), 3) for i in range(js.get_numaxes())]
    buttons = [js.get_button(i) for i in range(js.get_numbuttons())]
    hats = [js.get_hat(i) for i in range(js.get_numhats())]

    print("\n--- SNAPSHOT ---")
    print(f"Axes ({len(axes)}): {axes}")
    print(f"Buttons ({len(buttons)}): {buttons}")
    print(f"Hats/D-pad ({len(hats)}): {hats}")
    print("---------------\n")

def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick/gamepad detected.")
        print("Try: plug it in (or ensure dongle is paired) and run again.")
        return

    js = pygame.joystick.Joystick(0)
    js.init()

    print("Gamepad detected:")
    print(f"  Name: {js.get_name()}")
    print(f"  Axes: {js.get_numaxes()}")
    print(f"  Buttons: {js.get_numbuttons()}")
    print(f"  Hats (D-pad): {js.get_numhats()}")
    print("\nPress buttons / move sticks. Ctrl+C to quit.\n")

    last_snapshot = 0.0

    try:
        while True:
            # Pump events
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    print(f"JOYBUTTONDOWN  index={event.button}")
                elif event.type == pygame.JOYBUTTONUP:
                    print(f"JOYBUTTONUP    index={event.button}")
                elif event.type == pygame.JOYAXISMOTION:
                    # event.axis is the axis index, event.value is -1.0..+1.0
                    # (Triggers may show up as axes too.)
                    if abs(event.value) > 0.10:  # deadband to reduce spam
                        print(f"JOYAXISMOTION  axis={event.axis} value={event.value:.3f}")
                elif event.type == pygame.JOYHATMOTION:
                    # D-pad / hat: (x,y) where each is -1,0,1
                    print(f"JOYHATMOTION   hat={event.hat} value={event.value}")

            # Periodic snapshot of all inputs
            now = time.time()
            if now - last_snapshot >= SNAPSHOT_EVERY_SEC:
                snapshot(js)
                last_snapshot = now

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        js.quit()
        pygame.joystick.quit()
        pygame.quit()

if __name__ == "__main__":
    main()
