# Stevia on the Pixel 8 Pro: prototype notes

This is a test of Stevia 0.58.0 (the on-screen keyboard from the Phosh project, GPL-3) on Hyprland, for issue #415.
It is a prototype from one phone (Pixel 8 Pro, husky) and one day of testing, nothing here is meant to be merged as it is. squeekboard stays the keyboard.

`stevia-0.58.0-hyprland-prototype.diff` applies on the upstream v0.58.0 tarball with `patch -p1`
(https://gitlab.gnome.org/World/Phosh/stevia/-/archive/v0.58.0/stevia-v0.58.0.tar.gz).
Build with `meson setup _build --prefix=/usr` (needs `glib2-devel`), then `ninja -C _build`.
Run it with `phosh-osk-stevia --replace` after stopping squeekboard.
It needs `completion-mode` set to `['manual','hint']` and the completer set to `hunspell` in the `mobi.phosh.osk` GSettings.

## What the patch does, by file

- Hyprland compatibility: `pos-wayland.c` and `pos-hw-tracker.c` no longer wait for phoc's `zphoc_device_state_v1` (Hyprland doesn't have it).
- Long-press accents that you can slide to: `pos-char-popup.c/.h`, `pos-osk-widget.c`. The popup is not modal, so one finger can press, slide to ί or έ and lift. This is the Greek tonos and dialytika case.
- Suggestions for the whole word around the caret, not only the word being typed: `pos-completer.c/.h`, `completers/pos-completer-hunspell.c`, `pos-input-surface.c`. Space takes the first suggestion and it replaces the whole word.
- Slide to delete: slide left on the letters to delete a character, slide left from backspace to delete words, and hold at the far left to keep deleting (`pos-osk-gesture.c/.h` with a test in `tests/test-osk-gesture.c`, wired in `pos-osk-widget.c` and `pos-input-surface.c`).
- Space bar: hold and drag moves the caret (Stevia's own caret mode, patched so the arrow keys get sent, not confirmed yet); a quick swipe left or right on the space bar changes the layout (new, not tested on the phone yet).
- Layout menu drawn inside the keyboard (`pos-osk-widget.c`, `pos-input-surface.c`, `ui/input-surface.ui`). The GTK popover's touch area was one row off from what is drawn (tapping Greek chose English). Stevia's log put the menu rows partly outside the keyboard surface at first, and moving them inside didn't fix the offset. My guess is that it is a separate popup window on a layer-shell surface and Hyprland's fractional scale (3.2 here) shifts its input; I didn't confirm that in the compositor. The menu now has the layouts and Word completion. The Keyboard Settings button and the paste icon are not in it yet.
- Hide when no window has focus (`pos-activation-filter.c`, `phosh-osk-stevia.c`): after leaving an app to the home screen Stevia's log shows no deactivate from the input method, so the keyboard stayed up. I don't know why the compositor didn't send one, and I didn't check whether squeekboard does the same.

The theme is not in the diff. `omamobile-keyboard-theme` (shell PR in my fork, not opened yet) writes CSS for Stevia's `pos-key` style context from the Omarchy `colors.toml`.

## What was tested, and how

Pixel 8 Pro, kernel 7.3.0-rc6, Hyprland, scale 3.2 (the keyboard is 420 logical px wide), omawrite as the text app, touch only.
I tested it by typing and filming. Stevia's own meson tests pass except `test-completers`, which fails here because the `mobi.phosh.osk.Completers.Pipe` schema isn't installed in the memory settings backend I ran it with (setup, not a code failure, but I didn't check it against the unpatched tree).

Worked on the phone:
- Starts on Hyprland with the patch above, about 183 MB resident with the Greek dictionary loaded.
- Greek and English layouts. Long-press accents with slide-to-select tested on Greek (η ή, ι ί ϊ ΐ, ο ό, ε έ); the English accents (é è ê ë) are in the layout but I didn't test them.
- Hunspell suggestion strip in English and Greek, space takes the first suggestion.
- The layout menu, after the fix above.
- It hides on the home screen and comes back when omawrite opens (one app, one text field).
- The Omarchy theme colours.

Written but only partly checked on the phone: slide delete, caret drag, whole-word replace, the space bar swipe.

Not done: selecting words with Shift and the space bar and a cut/copy/paste menu, tap on the globe for the next layout (it opens the menu), the paste icon, keyboard height, a home for Keyboard Settings, a systemd unit or package, and any second device.
Not checked: other scales, landscape, password fields, a terminal, apps that don't use text-input v3, suspend and resume, a long run.

Hunspell only corrects and suggests the current word. Real word completion needs presage or a frequency list through the pipe completer.
