# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
import re

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
        "v22.12",
        "v23.06",
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
    "lenovo-a6000": "Lenovo A6000",
    "lenovo-a6010": "Lenovo A6010",
    "motorola-harpia": "Motorola Moto G4 Play",
    "nokia-n900": "Nokia N900",
    "odroid-hc2": "ODROID HC2",
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
    "samsung-serranove": "Samsung Galaxy S4 Mini Value Edition",
    "shift-axolotl": "SHIFT SHIFT6mq",
    "wileyfox-crackling": "Wileyfox Swift",
    "xiaomi-beryllium": "Xiaomi POCO F1",
    "xiaomi-scorpio": "Xiaomi Mi Note 2",
    "xiaomi-wt88047": "Xiaomi Redmi 2",
}

# Build configuration, can be overridden per device/branch in 'images' below
branch_config_default = {
    # Schedule a new image each {date-interval} days, start at {date-start}.
    "date-interval": 7,
    "date-start": "2021-07-21",  # Wednesday

    # User interfaces to build. At least one UI must be set for each device,
    # otherwise no image for that device will be built.
    "ui": [
        "phosh",
        "plasma-mobile",
        "sxmo-de-sway",
    ],

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
                "ui": [
                    "console",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "asus-me176c": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "bq-paella": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "fairphone-fp4": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "lenovo-a6000": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "lenovo-a6010": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "motorola-harpia": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "nokia-n900": {
        "branch_configs": {
            "all": {
                "ui": [
                    "i3wm",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "odroid-hc2": {
        "branch_configs": {
            "all": {
                "ui": [
                    "console",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "oneplus-enchilada": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "oneplus-fajita": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "pine64-pinebookpro": {
        "branch_configs": {
            "all": {
                "ui": [  # "plasma-desktop" is disabled, see pma#1623
                    "console",
                    "gnome",
                    "sway",
                    "phosh",
                ],
                "installer": True,
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "pine64-pinephone": {
        "branch_configs": {
            "all": {
                "installer": True,
            },
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "pine64-pinephonepro": {
        "branch_configs": {
            "all": {
                "installer": True,
            },
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "pine64-rockpro64": {
        "branch_configs": {
            "all": {
                "ui": [
                    "console",
                    "plasma-bigscreen",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "purism-librem5": {
        "branch_configs": {
            "all": {
                "installer": True,
            },
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-a3": {
        "branch_configs": {
            "master": {
                "ui": [
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                    "gnome-mobile",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-a5": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-e7": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-espresso10": {
        "branch_configs": {
            "all": {
                "ui": [
                    "phosh",
                    "xfce4",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "samsung-espresso7": {
        "branch_configs": {
            "all": {
                "ui": [
                    "phosh",
                    "xfce4",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
            },
        },
    },
    "samsung-grandmax": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-gt510": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-gt58": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-m0": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
                "ui": [
                    "phosh",
                    "sxmo-de-sway",
                ],
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-serranove": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "shift-axolotl": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "wileyfox-crackling": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "xiaomi-beryllium": {
        "branch_configs": {
            "all": {
                "kernels": [
                    "tianma",
                    "ebbg",
                ],
            },
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "xiaomi-scorpio": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "xiaomi-wt88047": {
        "branch_configs": {
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
            "v22.12": {
                "date-start": "2022-12-18",  # Sunday
            },
            "v23.06": {
                "date-start": "2023-06-05",  # Monday
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "plasma-mobile",
                    "sxmo-de-sway",
                ],
            },
        },
    },
}
