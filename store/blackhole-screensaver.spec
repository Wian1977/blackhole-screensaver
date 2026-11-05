Name:           blackhole-screensaver
Version:        1.1.0
Release:        1%{?dist}
Summary:        Real-physics Schwarzschild black-hole OpenGL screensaver
License:        MIT
URL:            https://github.com/Wian1977/blackholescreensaver
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz
BuildArch:      noarch

Requires:       python3
Requires:       python3-gobject
Requires:       gtk3
Requires:       python3-xlib
Requires:       mesa-libGL

%description
A native OpenGL screensaver that renders a Schwarzschild black hole live on the
GPU: gravitational lensing via geodesic integration, an accretion disk with
relativistic beaming and Doppler/gravitational redshift, and a lensed star
field. A desktop-independent daemon launches it full-screen on idle or lock.

%prep
%setup -q -n blackholescreensaver-%{version}

%install
APP=%{buildroot}%{_datadir}/blackhole-screensaver
mkdir -p "$APP" %{buildroot}%{_bindir} \
         %{buildroot}%{_datadir}/applications/screensavers \
         %{buildroot}%{_datadir}/applications \
         %{buildroot}%{_sysconfdir}/xdg/autostart
cp *.py "$APP/"
cp *.bin "$APP/" 2>/dev/null || true
cp -r plugin "$APP/"

cat > %{buildroot}%{_bindir}/blackhole-screensaver <<'SH'
#!/bin/sh
exec python3 /usr/share/blackhole-screensaver/bh_gl.py "$@"
SH
chmod 755 %{buildroot}%{_bindir}/blackhole-screensaver

cat > %{buildroot}%{_bindir}/blackhole-daemon <<'SH'
#!/bin/sh
exec python3 /usr/share/blackhole-screensaver/blackhole-daemon.py "$@"
SH
chmod 755 %{buildroot}%{_bindir}/blackhole-daemon

sed -e "s|@BH_GL@|%{_datadir}/blackhole-screensaver/bh_gl.py|" \
    blackhole.desktop.in > %{buildroot}%{_datadir}/applications/screensavers/blackhole.desktop
sed -e "s|@BH_GL@|%{_datadir}/blackhole-screensaver/bh_gl.py|" \
    -e "s|@ICON@|%{_datadir}/blackhole-screensaver/plugin/blackhole.png|" \
    blackhole-app.desktop.in > %{buildroot}%{_datadir}/applications/blackhole-screensaver.desktop

cat > %{buildroot}%{_sysconfdir}/xdg/autostart/blackhole-daemon.desktop <<'DE'
[Desktop Entry]
Type=Application
Name=Black Hole Screensaver Daemon
Comment=DE-independent idle/lock screensaver launcher
Exec=blackhole-daemon
Terminal=false
X-GNOME-Autostart-enabled=true
DE

%files
%license LICENSE
%{_bindir}/blackhole-screensaver
%{_bindir}/blackhole-daemon
%{_datadir}/blackhole-screensaver/
%{_datadir}/applications/screensavers/blackhole.desktop
%{_datadir}/applications/blackhole-screensaver.desktop
%{_sysconfdir}/xdg/autostart/blackhole-daemon.desktop

%changelog
* Thu Nov 05 2026 Wian1977 <blackhole@example.com> - 1.1.0-1
- Initial RPM package
