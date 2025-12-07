# PathfinderBot – Auto-Start Gamepad Drive on Boot

This guide shows how to configure your Raspberry Pi 4–based PathfinderBot to automatically start the mecanum gamepad drive script after boot.

- Robot user: `robot`
- Script path: `/home/robot/code/pf_mecanum_gamepad_drive.py`
- Goal: run the script automatically at boot using `systemd`, with the working directory set to `/home/robot/code` so relative imports and files work.

---

## 1. Test the script manually

On the robot, make sure the script runs correctly **from the absolute path**:

```bash
sudo python3 /home/robot/code/pf_mecanum_gamepad_drive.py
```

- If your system only uses `python`, change the command to:

  ```bash
  sudo python /home/robot/code/pf_mecanum_gamepad_drive.py
  ```

Once you confirm it runs as expected, press `Ctrl + C` to stop it.

---

## 2. Create the systemd service file

Create a new service file called `pf_mecanum_gamepad.service`:

```bash
sudo nano /etc/systemd/system/pf_mecanum_gamepad.service
```

Paste in the following content (adjust the `ExecStart` line if your Python path is different). You can check your Python path with `which python3`:

```ini
[Unit]
Description=PathfinderBot mecanum gamepad drive
After=network.target multi-user.target

[Service]
Type=simple

# Start in the code folder so relative imports and files work
WorkingDirectory=/home/robot/code

# Use python3 or python as appropriate
ExecStart=/usr/bin/python3 /home/robot/code/pf_mecanum_gamepad_drive.py

# Restart service if it crashes
Restart=on-failure
RestartSec=2

# Give the script a little time to shut down cleanly
TimeoutStopSec=10

[Install]
# Start this service when the system reaches multi-user mode (normal console boot)
WantedBy=multi-user.target
```

Save and exit:

- Press `Ctrl + O`, then `Enter` to save.
- Press `Ctrl + X` to exit.

> **Note:** If `which python3` returns a different path (for example `/usr/bin/python`), update the `ExecStart` line to match.

---

## 3. Reload systemd and enable the service

Tell `systemd` to pick up the new service file:

```bash
sudo systemctl daemon-reload
```

Enable the service so it starts **automatically on boot**:

```bash
sudo systemctl enable pf_mecanum_gamepad.service
```

You should no longer see any warnings about “no installation config.”

---

## 4. Start and check the service now

Start the service without rebooting:

```bash
sudo systemctl start pf_mecanum_gamepad.service
```

Check its status:

```bash
sudo systemctl status pf_mecanum_gamepad.service
```

You should see something like:

- `Active: active (running)` if everything is working.
- If there are errors, they will appear in this status output.

---

## 5. View logs for debugging

To see recent logs and any `print()` output from your script:

```bash
journalctl -u pf_mecanum_gamepad.service -n 50 -f
```

- `-n 50` shows the last 50 log lines.
- `-f` follows new log lines in real time (press `Ctrl + C` to stop following).

Use this to diagnose import errors, joystick problems, or GPIO issues.

---

## 6. Test on reboot

Reboot the robot to verify the script auto-starts:

```bash
sudo reboot
```

After the Pi finishes booting, your PathfinderBot should automatically start the `pf_mecanum_gamepad_drive.py` script.

You can confirm it’s running with:

```bash
sudo systemctl status pf_mecanum_gamepad.service
```

---

## 7. Stop or disable the auto-start (optional)

If you ever want to stop the service or prevent it from starting on boot:

- **Stop it right now:**

  ```bash
  sudo systemctl stop pf_mecanum_gamepad.service
  ```

- **Disable auto-start on boot:**

  ```bash
  sudo systemctl disable pf_mecanum_gamepad.service
  ```

You can re-enable it anytime with:

```bash
sudo systemctl enable pf_mecanum_gamepad.service
```

---

## 8. Common tweaks

### Change the Python interpreter

If you need to use a specific Python version or virtual environment, update the `ExecStart` line. Examples:

```ini
ExecStart=/usr/bin/python /home/robot/code/pf_mecanum_gamepad_drive.py
```

or

```ini
ExecStart=/home/robot/.venv/bin/python /home/robot/code/pf_mecanum_gamepad_drive.py
```

### Confirm the working directory

If you want to double-check that the service starts in `/home/robot/code`, temporarily add this near the top of your Python script:

```python
import os
print("CWD is:", os.getcwd())
```

Then check the logs with:

```bash
journalctl -u pf_mecanum_gamepad.service -n 50 -f
```

You should see:

```text
CWD is: /home/robot/code
```

If so, your auto-start configuration is good to go.
