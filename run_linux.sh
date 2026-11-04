#!/usr/bin/env bash
# Innioasis Updater CE - Linux launcher
#
# Installs the rewritten Innioasis Updater from the latest release, or runs it
# once without installing. No sudo, no system packages, no Python.
#
#   bash run_linux.sh              choose install or run once
#   bash run_linux.sh install      install the app
#   bash run_linux.sh run          run once without installing
#
# The AppImage comes from y1-community/innioasis-updater first, so first
# downloads and upgrades stay separately countable. The portable .zip comes
# from y1-community/updater-ce-neo, which owns the portable packages.

set -u

PRIMARY_REPO="y1-community/innioasis-updater"
PORTABLE_REPO="y1-community/updater-ce-neo"
SITE="https://innioasis.app/guide.html"
APP_NAME="Innioasis Updater"

say() { printf '%s\n' "$*"; }
fail() { printf '\n%s\n\nOpen %s to download the app.\n' "$*" "$SITE"; }

pause() {
    [ -t 0 ] && { printf '\nPress Enter to close.'; read -r _; }
}

# Reconnect to the terminal when this script is piped from curl.
if [ ! -t 0 ] && [ -r /dev/tty ]; then
    exec </dev/tty
fi

case "$(uname -m 2>/dev/null)" in
    x86_64 | amd64) ARCH="x64" ;;
    aarch64 | arm64) ARCH="arm64" ;;
    *)
        fail "This computer's processor is not supported by the ready-made builds."
        pause
        exit 1
        ;;
esac

download() {
    # download URL DESTINATION
    if command -v curl >/dev/null 2>&1; then
        curl -fL --retry 2 --connect-timeout 15 --progress-bar -o "$2" "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --show-progress -O "$2" "$1"
    else
        return 1
    fi
}

url_ok() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsIL --connect-timeout 12 -o /dev/null "$1" >/dev/null 2>&1
    else
        wget --spider -q -T 12 "$1" >/dev/null 2>&1
    fi
}

asset_url() {
    # asset_url REPO NAME... -> first asset that exists
    local repo="$1"
    shift
    local name url
    for name in "$@"; do
        url="https://github.com/${repo}/releases/latest/download/${name}"
        if url_ok "$url"; then
            printf '%s\n' "$url"
            return 0
        fi
    done
    return 1
}

resolve_appimage() {
    local names
    if [ "$ARCH" = "arm64" ]; then
        names="UpdaterCE-arm64.appimage UpdaterCE-arm64.AppImage"
    else
        names="UpdaterCE.AppImage UpdaterCE.appimage"
    fi
    # shellcheck disable=SC2086
    asset_url "$PRIMARY_REPO" $names || asset_url "$PORTABLE_REPO" $names
}

resolve_zip() {
    local names
    if [ "$ARCH" = "arm64" ]; then
        names="UpdaterCE-Linux-Portable-arm64.zip Updater-CE-Linux-Portable-arm64.zip"
    else
        names="UpdaterCE-Linux-Portable.zip Updater-CE-Linux-Portable.zip"
    fi
    # shellcheck disable=SC2086
    asset_url "$PORTABLE_REPO" $names || asset_url "$PRIMARY_REPO" $names
}

write_desktop_entry() {
    local exec_path="$1"
    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p "$desktop_dir" 2>/dev/null || return 0
    cat >"$desktop_dir/innioasis-updater-ce.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Firmware updates for Innioasis players
Exec="$exec_path"
Terminal=false
Categories=Utility;
Icon=system-software-update
EOF
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$desktop_dir" >/dev/null 2>&1 || true
    fi
}

fuse_ok() {
    [ -e /dev/fuse ] && { command -v fusermount3 >/dev/null 2>&1 || command -v fusermount >/dev/null 2>&1; }
}

install_appimage() {
    local url dest launcher flag
    url=$(resolve_appimage) || return 1
    dest="$HOME/.local/bin/Innioasis-Updater.AppImage"
    launcher="$HOME/.local/bin/innioasis-updater"
    mkdir -p "$HOME/.local/bin" 2>/dev/null || return 1
    say "Downloading $APP_NAME…"
    download "$url" "$dest.part" || { rm -f "$dest.part"; return 1; }
    mv -f "$dest.part" "$dest" || return 1
    chmod +x "$dest" 2>/dev/null || true
    if fuse_ok; then
        flag=""
    else
        flag=" --appimage-extract-and-run"
    fi
    cat >"$launcher" <<EOF
#!/bin/sh
exec "$dest"$flag "\$@"
EOF
    chmod +x "$launcher" 2>/dev/null || true
    write_desktop_entry "$launcher"
    say "Installed. Open $APP_NAME from your app menu."
    return 0
}

install_zip() {
    local url work target staging exe
    url=$(resolve_zip) || return 1
    work=$(mktemp -d 2>/dev/null) || return 1
    target="$HOME/.local/share/innioasis-updater-ce"
    staging="$target.part"
    say "Downloading $APP_NAME…"
    if ! download "$url" "$work/app.zip"; then
        rm -rf "$work"
        return 1
    fi
    rm -rf "$staging" 2>/dev/null
    mkdir -p "$staging" 2>/dev/null || { rm -rf "$work"; return 1; }
    if command -v unzip >/dev/null 2>&1; then
        unzip -q "$work/app.zip" -d "$staging" >/dev/null 2>&1 || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m zipfile -e "$work/app.zip" "$staging" >/dev/null 2>&1 || true
    fi
    rm -rf "$work"

    # Collapse a single top-level folder so the launcher is easy to find.
    if [ "$(find "$staging" -mindepth 1 -maxdepth 1 | wc -l)" = "1" ]; then
        local only
        only=$(find "$staging" -mindepth 1 -maxdepth 1)
        if [ -d "$only" ]; then
            mv "$only"/* "$staging"/ 2>/dev/null || true
            rmdir "$only" 2>/dev/null || true
        fi
    fi

    exe=$(find "$staging" -maxdepth 3 -type f \
        \( -name "Innioasis Updater" -o -name "Innioasis-Updater" -o -name "UpdaterCE" -o -name "innioasis-updater" \) \
        -print -quit 2>/dev/null)
    if [ -z "$exe" ]; then
        rm -rf "$staging"
        return 1
    fi
    chmod +x "$exe" 2>/dev/null || true
    rm -rf "$target" 2>/dev/null
    mv "$staging" "$target" 2>/dev/null || { rm -rf "$staging"; return 1; }
    exe="$target/${exe#"$staging"/}"
    mkdir -p "$HOME/.local/bin" 2>/dev/null || true
    cat >"$HOME/.local/bin/innioasis-updater" <<EOF
#!/bin/sh
exec "$exe" "\$@"
EOF
    chmod +x "$HOME/.local/bin/innioasis-updater" 2>/dev/null || true
    write_desktop_entry "$HOME/.local/bin/innioasis-updater"
    say "Installed. Open $APP_NAME from your app menu."
    return 0
}

install_app() {
    if install_appimage; then
        return 0
    fi
    say "The AppImage is unavailable. Using the portable .zip instead."
    if install_zip; then
        return 0
    fi
    fail "The download could not be completed."
    return 1
}

run_once() {
    local url work dest exe cmd
    work=$(mktemp -d 2>/dev/null) || { fail "A temporary folder could not be created."; return 1; }

    if url=$(resolve_appimage); then
        dest="$work/Innioasis-Updater.AppImage"
        say "Downloading $APP_NAME…"
        if download "$url" "$dest"; then
            chmod +x "$dest" 2>/dev/null || true
            if fuse_ok; then
                (nohup "$dest" >/dev/null 2>&1 &) 2>/dev/null
            else
                (nohup "$dest" --appimage-extract-and-run >/dev/null 2>&1 &) 2>/dev/null
            fi
            say "$APP_NAME is starting."
            return 0
        fi
    fi

    if url=$(resolve_zip); then
        say "The AppImage is unavailable. Using the portable .zip instead."
        if download "$url" "$work/app.zip"; then
            if command -v unzip >/dev/null 2>&1; then
                unzip -q "$work/app.zip" -d "$work/app" >/dev/null 2>&1 || true
            elif command -v python3 >/dev/null 2>&1; then
                python3 -m zipfile -e "$work/app.zip" "$work/app" >/dev/null 2>&1 || true
            fi
            exe=$(find "$work/app" -maxdepth 4 -type f \
                \( -name "Innioasis Updater" -o -name "Innioasis-Updater" -o -name "UpdaterCE" -o -name "innioasis-updater" \) \
                -print -quit 2>/dev/null)
            if [ -n "$exe" ]; then
                chmod +x "$exe" 2>/dev/null || true
                (nohup "$exe" >/dev/null 2>&1 &) 2>/dev/null
                say "$APP_NAME is starting."
                return 0
            fi
        fi
    fi

    fail "The download could not be completed."
    return 1
}

printf '\n%s\n\n' "$APP_NAME"
printf '  1) Install it on this computer\n'
printf '  2) Run it once\n'
printf '  3) Quit\n\n'
printf 'Choose 1-3: '
read -r choice

case "$choice" in
    1) install_app ;;
    2) run_once ;;
    *) say "Nothing changed." ;;
esac

pause
