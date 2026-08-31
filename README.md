# airMouse

**Sticky fingers? Not to worry.**

Control your Mac using hand gestures and, of course, your webcam.

airMouse tracks the 21 landmarks of your hand and translates them into gestures for moving the cursor, dragging, scrolling, changing volume and brightness, pausing the recognition, and more.

For now, **macOS only**.

> A demo GIF here would probably explain the whole thing better than the rest of this README.

---

## Gestures

So, how do we use this?

| Action | Gesture |
| --- | --- |
| **Move** | Open your hand and move your palm |
| **Drag** | Touch your thumb and middle finger while keeping the pinky raised |
| **Right Click** | Touch your thumb and ring finger while keeping the pinky raised |
| **Scroll** | Touch your thumb and index finger and tilt the index finger |
| **Volume** | Keep your index finger raised and change the distance between thumb and index |
| **Brightness** | Keep your index and pinky raised and change the distance between thumb and index |
| **Pause** | Hold a closed fist for a moment |
| **Resume** | Hold a peace sign ✌️ for a moment |
| **Quit** | Hold index, middle and ring fingers up while touching thumb to pinky. An american 3 (watch Inglorious Basterds)|

Some gestures such as **Pause**, **Resume**, and **Quit** need to remain stable for several frames before being triggered.

This is intentional.

Otherwise waving your hand around could occasionally become the computer equivalent of pulling the plug.

When using Volume or Brightness, a little bubblegum line appears between your thumb and index finger. As you move them apart, the line stretches and gets thinner, giving you a visual reference for the current value. Is nice.

---

## Requirements

- macOS
- Python **3.10–3.12**
- A webcam
- Camera permission for your terminal application
- Accessibility permission for your terminal application
- Optional: the `brightness` command for brightness control

### A note about Python

I've noticed that computer vision libraries tend to behave a little better when you're not running whatever Python version came out five minutes ago.

The latest version I've personally used successfully with this project is:

```text
Python 3.11.13
```

So that's the version I recommend.

My preferred setup is:

- `pyenv` to install and select the Python version
- `venv` to create an isolated environment for the project

But you can do it as you like it.
---

## Installation

Clone the repository:

```bash
git clone https://github.com/niCodeLine/airmouse.git
cd airmouse
```

Then create the environment and install everything:

```bash
pyenv install 3.11.13
pyenv local 3.11.13

python -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[runtime,dev]"
```

You can check that everything is using the expected Python version with:

```bash
python --version
```

It should show something like:

```text
Python 3.11.13
```

If you only want to **run airMouse** and don't care about tests or development tools, install only the runtime dependencies:

```bash
python -m pip install -e ".[runtime]"
```

---

## Run

Once installed, just run:

```bash
airmouse
```

A little window should pop up showing the webcam feed and the detected hand landmarks.

The first run may take a little while while everything gets initialized.

macOS will probably also ask you for some permissions.

Go to:

**System Settings → Privacy & Security**

and make sure your terminal application has access to:

- **Camera**
- **Accessibility**

Without Camera permission, airMouse can't see you.

Without Accessibility permission, it can see you perfectly well but can't boss your mouse around.

---

## Useful options

Use another camera:

```bash
airmouse --camera 1
```

Run without showing the webcam preview:

```bash
airmouse --no-preview
```

Adjust cursor smoothing and pinch sensitivity:

```bash
airmouse --smoothing 0.25 --pinch-threshold 0.30
```

---

## How to stop it

You have a few options.

Press:

```text
Q
```

while the preview window is selected.

You can also use the **Quit gesture** (american 3).

PyAutoGUI's corner failsafe is kept enabled as well, so moving the pointer into a screen corner will abort mouse control.

Useful if your hand suddenly decides it has different plans for your computer.

---

## How it works

The project is split into three intentionally separate parts:

### `hand.py`

Models the 21 normalized hand landmarks and handles the geometry between them.

### `gestures.py`

Takes that geometry and decides what you're actually trying to do with your fingers.

### `runtime.py`

Handles the webcam loop and the actual macOS side effects:

- moving the cursor
- dragging
- clicking
- scrolling
- changing volume
- changing brightness
- etc.

Basically:

```text
webcam
   ↓
21 hand landmarks
   ↓
geometry
   ↓
gesture recognition
   ↓
macOS action
```

Keeping the gesture logic separate from the webcam and desktop code also means it can be tested deterministically without needing a camera connected.

Which is considerably nicer than running the entire application while repeatedly making hand signs at your laptop.

---

## Development

If you followed the recommended installation above, the development dependencies are already installed.

Run the tests with:

```bash
pytest
```

And check the code with Ruff:

```bash
ruff check .
```

The core tests don't require OpenCV, MediaPipe, or even a connected webcam.

So you can test the actual gesture logic without having your mouse flying around the screen.

---

## Privacy

All webcam frames are processed **locally**.

airMouse does not store or transmit camera frames anywhere.

Your questionable hand gestures remain between you and your computer.

---

## License

MIT © Nico Spok