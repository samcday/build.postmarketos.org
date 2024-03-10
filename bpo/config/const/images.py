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
        "v23.12",
    ]

# UIs value used in the "images" variable below for various laptop/convertible/
# tablet devices
ui_laptop_convertible = [
    "console",
    "gnome",
    "phosh",
    "plasma-desktop",
    "sway",
]

# UIs value used in the "images" variable below for various laptop/convertible/
# tablet devices without GPU support
ui_laptop_convertible_no_gpu = [
    "console",
    "xfce4",
    "mate",
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
    "generic-x86_64": "Generic x86_64 Device",
    "google-gru": "Google Gru Chromebooks",
    "google-kukui": "Google Kukui Chromebooks",
    "google-oak": "Google Oak Chromebooks",
    "google-peach-pit": "Samsung Chromebook 2 11.6\"",
    "google-snow": "Samsung Chromebook",
    "google-trogdor": "Google Trogdor Chromebooks",
    "google-veyron": "Google Veyron Chromebooks",
    "google-x64cros": "Google Chromebooks with x64 CPU",
    "lenovo-a6000": "Lenovo A6000",
    "lenovo-a6010": "Lenovo A6010",
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
    "ui": [
        "gnome-mobile",
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
        },
    },
    "asus-me176c": {
    },
    "bq-paella": {
    },
    "fairphone-fp4": {
    },
    "generic-x86_64": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible,
            },
        },
    },
    "google-gru": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible,
            },
        },
    },
    "google-kukui": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible,
            },
        },
    },
    "google-oak": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible_no_gpu,
            },
        },
    },
    "google-peach-pit": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": [ # laptop
                    "console",
                    "gnome",
                    "plasma-desktop",
                    "sway",
                ],
            },
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": [
                    "console",
                    "gnome",
                    "sway",
                ],
            },
        },
    },
    "google-snow": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "master": {
                "ui": [
                    "console",
                    "gnome",
                    "plasma-desktop",
                    "sway",
                ],
            },
            "v23.12": {
                # There is no GPU support in 23.12
                "ui": ui_laptop_convertible_no_gpu,
            },
        },
    },
    "google-trogdor": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible,
            },
        },
    },
    "google-veyron": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible,
            },
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": [
                    "console",
                    "gnome",
                    "phosh",
                    "sway",
                ],
            }
        },
    },
    "google-x64cros": {
        "branches": [
            "master",
            "v23.12",
        ],
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
                "ui": ui_laptop_convertible,
            },
        },
    },
    "lenovo-a6000": {
    },
    "lenovo-a6010": {
    },
    "motorola-harpia": {
    },
    "nokia-n900": {
        "branch_configs": {
            "all": {
                "ui": [
                    "i3wm",
                ],
            },
            "master": {
                "date-start": "2023-07-07",  # Friday
            },
        },
    },
    "nvidia-tegra-armv7": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": ui_laptop_convertible_no_gpu,
            },
        },
    },
    "odroid-xu4": {
        "branches": [
            "master",
            "v23.12",
        ],
        "branch_configs": {
            "all": {
                "ui": [
                    "console",
                ],
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
                "ui": [  # "plasma-desktop" is disabled, see pma#1623
                    "console",
                    "gnome",
                    "sway",
                    "phosh",
                ],
            },
        },
    },
    "pine64-pinephone": {
    },
    "pine64-pinephonepro": {
    },
    "pine64-rockpro64": {
        "branch_configs": {
            "all": {
                "ui": [
                    "console",
                    "plasma-bigscreen",
                ],
            },
            # Disable plasma bigscreen for master:
            # https://gitlab.com/postmarketOS/pmaports/-/issues/2650
            "master": {
                "ui": [
                    "console",
                ],
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
                "ui": [
                    "gnome-mobile",
                    "phosh",
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
        },
    },
    "samsung-grandmax": {
        "branch_configs": {
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "sxmo-de-sway",
                ],
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
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-manta": {
        "branches": [
            "master",
        ],
        "branch_configs": {
            "all": {
                "ui": [
                    "console",
                    "gnome-mobile",
                    "phosh",
                    "sxmo-de-sway",
                ],
            },
        },
    },
    "samsung-serranove": {
        "branch_configs": {
            # Disable plasma for master:
            # https://gitlab.alpinelinux.org/alpine/aports/-/issues/15638
            "master": {
                "ui": [
                    "gnome-mobile",
                    "phosh",
                    "sxmo-de-sway",
                ],
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
        "branches": [
            "master",
            "v23.12",
        ],
    },
    "xiaomi-markw": {
        "branches": [
            "master",
            "v23.12",
        ],
    },
    "xiaomi-mido": {
        "branches": [
            "master",
            "v23.12",
        ],
    },
    "xiaomi-scorpio": {
    },
    "xiaomi-tissot": {
        "branches": [
            "master",
            "v23.12",
        ],
    },
    "xiaomi-vince": {
        "branches": [
            "master",
            "v23.12",
        ],
    },
    "xiaomi-wt88047": {
    },
    "xiaomi-ysl": {
        "branches": [
            "master",
            "v23.12",
        ],
    },
}
