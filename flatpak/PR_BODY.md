Title: Add io.github.Wian1977.BlackHoleScreensaver

---

Black Hole Screensaver is a Linux screensaver that draws a Schwarzschild
black hole with its accretion disk and gravitational lensing, all on the GPU.
It is a small Python + OpenGL (GLSL 3.3) program, no frameworks, no looping
video. A desktop-independent daemon waits for the usual screen-saver signals
(FreeDesktop / KDE / Cinnamon / GNOME / MATE) and puts the animation
full-screen when the session locks or goes idle. Works on both X11 and
Wayland through GTK3.

While it is showing, the keys do things instead of closing it:
M toggles camera motion, L toggles star lensing, space pauses, S mutes the
ambient tone, 1/2/3 pick quality, [ and ] change distance, B toggles disk
brightness, H shows or hides the help overlay. Moving the mouse does nothing.
Esc is the only key that dismisses it.

I have been running it daily on my own Linux Mint (Cinnamon, X11) and a
Wayland box since early November 2026, and I cut tagged .deb releases on
GitHub. I plan to keep maintaining it.

Source and releases: https://github.com/Wian1977/blackhole-screensaver

## Submission checklist

- [x] Please describe the application briefly.
- [x] Please attach a video showcasing the application on Linux using the Flatpak.
- [x] The Flatpak ID follows all the rules listed in the ID guidelines.
- [x] I have read and followed all the submission guidelines.
- [x] The application has a meaningful development history, evidence of real-world use, and a clear commitment to ongoing maintenance, as required by the requirements.
- [x] I have disclosed any AI-generated material included in the application or its Flathub packaging, as required by the requirements.
- [ ] I have not used AI tools or agents to generate or automate this submission pull request or its review interactions.
- [x] Your role in the project (author, developer, or upstream contributor)

AI disclosure: I used an AI coding assistant to help draft the Flatpak manifest,
the AppStream metainfo, and this submission description. The application source
code itself is my own original work. I am the upstream author and I am
submitting this myself.

## Permission notes (finish-args)

The daemon only subscribes to the screen-saver ActiveChanged signal on those
bus names. It never owns a name or talks to anything else, so the surface is
small. wayland, fallback-x11 and dri are just what the GL window needs. The
XDG autostart .desktop starts the daemon with the user session, which is the
whole point of a screensaver.
Video (live Flatpak capture): https://github.com/Wian1977/blackhole-screensaver/releases/download/v1.1.0/blackhole_cast.mp4
