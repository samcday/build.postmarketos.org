# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
import re

def get_ui_list(chassis, supports_gpu=True, exclude_ui=[], add_ui=[]):
    ui = set()

    if "handset" in chassis:
        if supports_gpu:
            ui.add("gnome-mobile")
            ui.add("phosh")
            ui.add("plasma-mobile")
            ui.add("sxmo-de-sway")
        else:
            ui.add("mate")
            ui.add("xfce4")
            ui.add("sxmo-de-dwm")

    if "convertible" in chassis or "tablet" in chassis:
        if supports_gpu:
            ui.add("phosh")
            ui.add("sxmo-de-sway")
        else:
            ui.add("mate")
            ui.add("xfce4")
            ui.add("sxmo-de-dwm")

    if "convertible" in chassis or "laptop" in chassis:
        ui.add("console")
        if supports_gpu:
            ui.add("gnome")
            ui.add("plasma-desktop")
            ui.add("sway")
        else:
            ui.add("mate")
            ui.add("xfce4")
            ui.add("i3wm")

    if "embedded" in chassis:
        ui.add("console")

    if exclude_ui:
        for ui_to_remove in exclude_ui:
            ui.remove(ui_to_remove)

    if add_ui:
        for ui_to_add in add_ui:
            ui.add(ui_to_add)

    return list(ui)

# Regular expressions for resulting dir and file names
pattern_dir = re.compile("^[0-9]{8}-[0-9]{4}$")
pattern_file = re.compile(
        "^[0-9]{8}-[0-9]{4}-postmarketOS-[a-z0-9._+-]+\\.img\\.xz"
        "(\\.sha(256|512))?$")

# Default password for regular (non-installer) images
password = "147147"

# Branches to build images for, can be overridden per device in 'images' below
branches_default = [
        "master",
        "v23.12",
        "v24.06",
    ]

# Prevent errors by listing explicitly allowed UIs here. Notably "none" is
# missing, as the UI does not follow the usual naming scheme
# (postmarketos-ui-none/APKBUILD doesn't exist). Code in bpo.jobs.build_image
# would try to extract the pkgver from the file and do something undefined.
# Use "console" instead.
ui_list = {
    "asteroid": "Asteroid",
    "console": "Console",
    "fbkeyboard": "Fbkeyboard",
    "gnome": "GNOME",
    "gnome-mobile": "GNOME Mobile",
    "i3wm": "i3",
    "kodi": "Kodi",
    "lxqt": "LXQt",
    "mate": "Mate",
    "phosh": "Phosh",
    "plasma-bigscreen": "Plasma Bigscreen",
    "plasma-desktop": "Plasma Desktop",
    "plasma-mobile": "Plasma Mobile",
    "shelli": "Shelli",
    "sway": "Sway",
    "sxmo-de-dwm": "Sxmo (dwm)",
    "sxmo-de-sway": "Sxmo (Sway)",
    "weston": "Weston",
    "xfce4": "XFCE4",
}

# Pretty name mapping for device codenames
devices = {
    "arrow-db410c": "Arrow DragonBoard 410c",
    "asus-me176c": "ASUS MeMO Pad 7",
    "bq-paella": "BQ Aquaris X5",
    "fairphone-fp4": "Fairphone 4",
    "fairphone-fp5": "Fairphone 5",
    "generic-x86_64": "Generic x86_64 Device",
    "google-asurada": "Google Asurada Chromebooks",
    "google-cherry": "Google Cherry Chromebooks",
    "google-corsola": "Google Corsola Chromebooks",
    "google-gru": "Google Gru Chromebooks",
    "google-kukui": "Google Kukui Chromebooks",
    "google-nyan-big": "Acer Chromebook 13 CB5-311",
    "google-nyan-blaze": "HP Chromebook 14 G3",
    "google-oak": "Google Oak Chromebooks",
    "google-peach-pi": "Samsung Chromebook 2 13.3\"",
    "google-peach-pit": "Samsung Chromebook 2 11.6\"",
    "google-snow": "Samsung Chromebook",
    "google-trogdor": "Google Trogdor Chromebooks",
    "google-veyron": "Google Veyron Chromebooks",
    "google-x64cros": "Google Chromebooks with x64 CPU",
    "lenovo-a6000": "Lenovo A6000",
    "lenovo-a6010": "Lenovo A6010",
    "microsoft-surface-rt": "Microsoft Surface RT",
    "motorola-harpia": "Motorola Moto G4 Play",
    "nokia-n900": "Nokia N900",
    "nvidia-tegra-armv7": "Nvidia Tegra armv7",
    "odroid-hc2": "ODROID HC2",
    "odroid-xu4": "ODROID XU4",
    "oneplus-enchilada": "OnePlus 6",
    "oneplus-fajita": "OnePlus 6T",
    "pine64-pinebookpro": "PINE64 Pinebook Pro",
    "pine64-pinephone": "PINE64 PinePhone",
    "pine64-pinephonepro": "PINE64 PinePhone Pro",
    "pine64-rockpro64": "PINE64 RockPro64",
    "purism-librem5": "Purism Librem5",
    "qemu-amd64": "QEMU amd64",  # just used for test suite
    "samsung-a3": "Samsung Galaxy A3 2015",
    "samsung-a5": "Samsung Galaxy A5 2015",
    "samsung-e7": "Samsung Galaxy E7",
    "samsung-espresso10": "Samsung Galaxy Tab 2 10.1\"",
    "samsung-espresso7": "Samsung Galaxy Tab 2 7.0\"",
    "samsung-grandmax": "Samsung Galaxy Grand Max",
    "samsung-gt510": "Samsung Galaxy Tab A 9.7 2015",
    "samsung-gt58": "Samsung Galaxy Tab A 8.0 2015",
    "samsung-m0": "Samsung Galaxy S III",
    "samsung-manta": "Google Nexus 10",
    "samsung-serranove": "Samsung Galaxy S4 Mini Value Edition",
    "shift-axolotl": "SHIFT SHIFT6mq",
    "wileyfox-crackling": "Wileyfox Swift",
    "xiaomi-beryllium": "Xiaomi POCO F1",
    "xiaomi-daisy": "Xiaomi Mi A2 Lite",
    "xiaomi-markw": "Xiaomi Redmi 4 Prime",
    "xiaomi-mido": "Xiaomi Redmi Note 4",
    "xiaomi-scorpio": "Xiaomi Mi Note 2",
    "xiaomi-tissot": "Xiaomi Mi A1",
    "xiaomi-vince": "Xiaomi Redmi 5 Plus",
    "xiaomi-wt88047": "Xiaomi Redmi 2",
    "xiaomi-ysl": "Xiaomi Redmi S2/Y2",
}

# Build configuration, can be overridden per device/branch in 'images' below
branch_config_default = {
    # Schedule a new image each {date-interval} days, start at {date-start}.
    "date-interval": 7,
    "date-start": "2021-07-21",  # Wednesday

    # User interfaces to build. At least one UI must be set for each device,
    # otherwise no image for that device will be built.
    "ui": get_ui_list(chassis=["handset"]),

    # Build images with the on-device installer. If set to False, build one
    # image without the installer. If set to True, build another image, which
    # wraps the first image with the installer.
    "installer": False,

    # To create additional images with other kernels selected, override this
    # variable. For qemu-amd64, this could be ["virt", "lts"].
    # https://postmarketos.org/multiple-kernels
    "kernels": [""],

    # How many images (image directories) to keep of one branch:device:ui
    # combination. Older images will get deleted to free up space.
    "keep": 3
}

# For each image you add here, make sure there is a proper wiki redirect for
# https://wiki.postmarketos.org/wiki/<codename>. That is what will show up in
# the generated readme.html!
images = {
    "arrow-db410c": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["embedded"]),
            },
        },
    },
    "asus-me176c": {
    },
    "bq-paella": {
    },
    "fairphone-fp4": {
    },
    "fairphone-fp5": {
        "branches": [
            "master",
            "v24.06",
        ],
    },
    "generic-x86_64": {
        "branches": [
            "master",
            "v24.06",
        ],
        "branch_configs": {
            "all": {
                # Disable plasma-desktop:
                # https://gitlab.com/postmarketOS/build.postmarketos.org/-/issues/136
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"],
                                  exclude_ui=["plasma-desktop"]),
                "kernels": [
                    "lts",
                ],
            },
        },
    },
    "google-asurada": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
        },
    },
    "google-cherry": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
        },
    },
    "google-corsola": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
        },
    },
    "google-gru": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
            },
        },
    },
    "google-kukui": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
            },
        },
    },
    "google-nyan-big": {
        "branches": [
            "master",
            "v24.06",
        ],
        "branch_configs": {
            "all": {
                "kernels": [
                    "nyan-big",
                    "nyan-big-fhd",
                ],
                "ui": get_ui_list(chassis=["laptop"], supports_gpu=False),
            },
        },
    },
    "google-nyan-blaze": {
        "branches": [
            "master",
            "v24.06",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"], supports_gpu=False),
            },
        },
    },
    "google-oak": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"], supports_gpu=False),
            },
        },
    },
    "google-peach-pi": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["laptop"], exclude_ui=["plasma-desktop"]),
            },
        },
    },
    "google-peach-pit": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["laptop"], exclude_ui=["plasma-desktop"]),
            },
        },
    },
    "google-snow": {
        "branch_configs": {
            "master": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
            "v23.12": {
                # There is no GPU support in 23.12
                "ui": get_ui_list(chassis=["laptop"], supports_gpu=False),
            },
        },
    },
    "google-trogdor": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
            },
        },
    },
    "google-veyron": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["laptop", "convertible"], exclude_ui=["plasma-desktop"]),
            }
        },
    },
    "google-x64cros": {
        "branch_configs": {
            "all": {
                "kernels": [
                    # "lts" kernel would be a bit better in theory, but it is
                    # too big to fit the cgpt_kpart partition:
                    #   % dd if=…/boot/vmlinuz.kpart of=/dev/installp1
                    #   dd: error writing '/dev/installp1': No space left on device
                    # Use "edge" instead, it actually misses only a few configs
                    # for these devices, nothing critical.
                    "edge",
                ],
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
            "v23.12": {
                # plasma-desktop fails to build for v23.12 (pma#2688). Work
                # around it by not building it, users can upgrade from the
                # existing images and it works for edge.
                "ui": get_ui_list(chassis=["laptop", "convertible"],
                                  exclude_ui=["plasma-desktop"]),
            },
        },
    },
    "lenovo-a6000": {
    },
    "lenovo-a6010": {
    },
    "microsoft-surface-rt": {
        "branches": [
            "master",
            "v24.06",
        ],
        "branch_configs": {
            "all": {
                # Tablet with detachable keyboard
                "ui": get_ui_list(chassis=["convertible"], supports_gpu=False),
            },
        },
    },
    "motorola-harpia": {
    },
    "nokia-n900": {
        "branch_configs": {
            "all": {
                # Handset with keyboard
                "ui": get_ui_list(chassis=["convertible"], supports_gpu=False),
            },
            "master": {
                "date-start": "2023-07-07",  # Friday
            },
        },
    },
    "nvidia-tegra-armv7": {
        "branches": [
            "master",
            "v24.06",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["convertible", "tablet", "handset"], supports_gpu=False),
            },
        },
    },
    "odroid-xu4": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["embedded"]),
            },
        },
    },
    "oneplus-enchilada": {
    },
    "oneplus-fajita": {
    },
    "pine64-pinebookpro": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
        },
    },
    "pine64-pinephone": {
    },
    "pine64-pinephonepro": {
    },
    "pine64-rockpro64": {
        "branch_configs": {
            # Disable plasma bigscreen for master, v24.06:
            # https://gitlab.com/postmarketOS/pmaports/-/issues/2650
            "all": {
                "ui": get_ui_list(chassis=["embedded"]),
            },
            "v23.12": {
                "ui": get_ui_list(chassis=["embedded"], add_ui=["plasma-bigscreen"]),
            },
        },
    },
    "purism-librem5": {
    },
    "samsung-a3": {
    },
    "samsung-a5": {
    },
    "samsung-e7": {
        "branch_configs": {
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["handset"], exclude_ui=["plasma-mobile"]),
            },
        },
    },
    "samsung-espresso10": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["tablet"], supports_gpu=False),
            },
        },
    },
    "samsung-espresso7": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["tablet"], supports_gpu=False),
            },
        },
    },
    "samsung-grandmax": {
        "branch_configs": {
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["handset"], exclude_ui=["plasma-mobile"]),
            },
        },
    },
    "samsung-gt510": {
    },
    "samsung-gt58": {
    },
    "samsung-m0": {
        "branch_configs": {
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["handset"], exclude_ui=["plasma-mobile"]),
            },
        },
    },
    "samsung-manta": {
        "branches": [
            "master",
            "v24.06",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["tablet"]),
            },
        },
    },
    "samsung-serranove": {
        "branch_configs": {
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": get_ui_list(chassis=["handset"], exclude_ui=["plasma-mobile"]),
            },
        },
    },
    "shift-axolotl": {
    },
    "wileyfox-crackling": {
    },
    "xiaomi-beryllium": {
        "branch_configs": {
            "all": {
                "kernels": [
                    "tianma",
                    "ebbg",
                ],
            },
        },
    },
    "xiaomi-daisy": {
    },
    "xiaomi-markw": {
    },
    "xiaomi-mido": {
    },
    "xiaomi-scorpio": {
    },
    "xiaomi-tissot": {
    },
    "xiaomi-vince": {
    },
    "xiaomi-wt88047": {
    },
    "xiaomi-ysl": {
    },
}
