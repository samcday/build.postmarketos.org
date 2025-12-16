# Copyright 2022 Oliver Smith
# SPDX-License-Identifier: AGPL-3.0-or-later
# What postmarketOS images to build with BPO. After modifying this file, test
# it with: "pytest test/test_config_const_images.py"
import re

def get_ui_list(chassis=["handset"], supports_gpu=True, exclude_ui=[], add_ui=[]):
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
        "^[0-9]{8}-[0-9]{4}-postmarketOS-[a-z0-9._+-]+(\\.img\\.xz|\\.zip)"
        "(\\.sha(256|512))?$")

# Default password for images
password = "147147"

# Branches to build images for, can be overridden per device in 'images' below
branches_default = [
        "master",
        "v25.06",
        "v25.12",
    ]

# Prevent errors by listing explicitly allowed UIs here. Notably "none" is
# missing, as the UI does not follow the usual naming scheme
# (postmarketos-ui-none/APKBUILD doesn't exist). Code in bpo.jobs.build_image
# would try to extract the pkgver from the file and do something undefined.
# Use "console" instead.
ui_list = {
    "asteroid": "Asteroid",
    "console": "Console",
    "cosmic": "COSMIC",
    "fbkeyboard": "Fbkeyboard",
    "gnome": "GNOME",
    "gnome-mobile": "GNOME Mobile",
    "i3wm": "i3",
    "kodi": "Kodi",
    "lxqt": "LXQt",
    "mate": "Mate",
    "os-installer": "Installer",
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
    "amlogic-aarch64-tvbox": "Amlogic Generic AArch64 TV Box",
    "arrow-db410c": "Arrow DragonBoard 410c",
    "asus-me176c": "ASUS MeMO Pad 7",
    "bq-paella": "BQ Aquaris X5",
    "fairphone-fp4": "Fairphone 4",
    "fairphone-fp5": "Fairphone 5",
    "generic-x86_64": "Generic x86_64 Device",
    "google-asurada": "Google Asurada Chromebooks",
    "google-bonito": "Google Pixel 3a XL",
    "google-cherry": "Google Cherry Chromebooks",
    "google-corsola": "Google Corsola Chromebooks",
    "google-gru": "Google Gru Chromebooks",
    "google-kukui": "Google Kukui Chromebooks",
    "google-nyan-big": "Acer Chromebook 13 CB5-311",
    "google-nyan-blaze": "HP Chromebook 14 G3",
    "google-oak": "Google Oak Chromebooks",
    "google-peach-pi": "Samsung Chromebook 2 13.3\"",
    "google-peach-pit": "Samsung Chromebook 2 11.6\"",
    "google-sargo": "Google Pixel 3a",
    "google-snow": "Samsung Chromebook",
    "google-trogdor": "Google Trogdor Chromebooks",
    "google-veyron": "Google Veyron Chromebooks",
    "google-x64cros": "Google Chromebooks with x64 CPU",
    "lenovo-21bx": "Lenovo Thinkpad X13s",
    "lenovo-a6000": "Lenovo A6000",
    "lenovo-a6010": "Lenovo A6010",
    "librecomputer-lafrite": "Libre Computer AML-S805X-AC",
    "librecomputer-lepotato": "Libre Computer AML-S905X-CC",
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
    "postmarketos-trailblazer": "PostmarketOS Trailblazer",
    "purism-librem5": "Purism Librem5",
    "qemu-amd64": "QEMU amd64",  # just used for test suite
    "qcom-msm8953": "Generic Qualcomm MSM8953",
    "qcom-sm7150": "Generic Qualcomm SM7150",
    "samsung-a3": "Samsung Galaxy A3 2015",
    "samsung-a5": "Samsung Galaxy A5 2015",
    "samsung-coreprimevelte": "Samsung Galaxy Core Prime VE LTE",
    "samsung-e7": "Samsung Galaxy E7",
    "samsung-espresso10": "Samsung Galaxy Tab 2 10.1\"",
    "samsung-espresso7": "Samsung Galaxy Tab 2 7.0\"",
    "samsung-grandmax": "Samsung Galaxy Grand Max",
    "samsung-gt510": "Samsung Galaxy Tab A 9.7 2015",
    "samsung-gt58": "Samsung Galaxy Tab A 8.0 2015",
    "samsung-m0": "Samsung Galaxy S III",
    "samsung-manta": "Google Nexus 10",
    "samsung-serranove": "Samsung Galaxy S4 Mini Value Edition",
    "samsung-starqltechn": "Samsung Galaxy S9 (China/Latam)",
    "shift-axolotl": "SHIFT SHIFT6mq",
    "wileyfox-crackling": "Wileyfox Swift",
    "xiaomi-beryllium": "Xiaomi POCO F1",
    "xiaomi-daisy": "Xiaomi Mi A2 Lite",
    "xiaomi-elish": "Xiaomi Mi Pad 5 Pro",
    "xiaomi-markw": "Xiaomi Redmi 4 Prime",
    "xiaomi-mido": "Xiaomi Redmi Note 4",
    "xiaomi-nabu": "Xiaomi Mi Pad 5",
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
    "date-start": "2025-06-20",  # Thursday

    # User interfaces to build. At least one UI must be set for each device,
    # otherwise no image for that device will be built.
    "ui": get_ui_list(),

    # Build images with android recovery zip
    "android-recovery-zip": False,

    # To create additional images with other kernels selected, override this
    # variable. For qemu-amd64, this could be ["virt", "lts"].
    # https://postmarketos.org/multiple-kernels
    "kernels": [""],

    # How many images (image directories) to keep of one branch:device:ui
    # combination. Older images will get deleted to free up space.
    "keep": 2
}

# For each image you add here, make sure there is a proper wiki redirect for
# https://wiki.postmarketos.org/wiki/<codename>. That is what will show up in
# the generated readme.html!
images = {
    "amlogic-aarch64-tvbox": {
        "branches": [
            "master",
            "v25.12",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet", "embedded"]),
                "kernels": [
                    "ugoos-am3",
                    "videostrong-kii-pro",
                    "xiaomi-aquaman",
                ],
            },
            "master": {
                "date-start": "2025-11-14",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "arrow-db410c": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["embedded"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "asus-me176c": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "bq-paella": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "fairphone-fp4": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "fairphone-fp5": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "generic-x86_64": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
                "kernels": [
                    "lts",
                ],
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"], add_ui=["cosmic", "os-installer"]),
            },
            "v25.06": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"], add_ui=["os-installer"]),
            },
            "v25.12": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"], add_ui=["os-installer"]),
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-asurada": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-bonito": {
        "branch_configs": {
            "all": {
                "kernels": [
                    "sdc",
                    "tianma",
                ],
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-cherry": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-corsola": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-gru": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-kukui": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-nyan-big": {
        "branches": [
            # Disabled on master:
            # https://gitlab.postmarketos.org/postmarketOS/pmaports/-/issues/3186
        ],
        "branch_configs": {
            "all": {
                "kernels": [
                    "nyan-big",
                    "nyan-big-fhd",
                ],
                "ui": get_ui_list(chassis=["laptop"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-nyan-blaze": {
        "branches": [
            # Disabled on master:
            # https://gitlab.postmarketos.org/postmarketOS/pmaports/-/issues/3186
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-oak": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-peach-pi": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-peach-pit": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-sargo": {
    },
    "google-snow": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-trogdor": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-veyron": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "google-x64cros": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"], add_ui=["os-installer"]),
                "kernels": [
                    # "lts" kernel would be a bit better in theory, but it is
                    # too big to fit the cgpt_kpart partition:
                    #   % dd if=…/boot/vmlinuz.kpart of=/dev/installp1
                    #   dd: error writing '/dev/installp1': No space left on device
                    "stable",
                ],
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.06": {
                "kernels": [
                    # "lts" kernel would be a bit better in theory, but it is
                    # too big to fit the cgpt_kpart partition:
                    #   % dd if=…/boot/vmlinuz.kpart of=/dev/installp1
                    #   dd: error writing '/dev/installp1': No space left on device
                    # Use "edge" instead, it actually misses only a few configs
                    # for these devices, nothing critical.
                    "edge",
                ],
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "lenovo-21bx": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"], add_ui=["os-installer"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
                "ui": get_ui_list(chassis=["laptop"], add_ui=["cosmic", "os-installer"]),
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "lenovo-a6000": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "librecomputer-lafrite": {
        "branches": [
            "master",
            "v25.12",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet", "embedded"]),
            },
            "master": {
                "date-start": "2025-11-14",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "librecomputer-lepotato": {
        "branches": [
            "master",
            "v25.12",
        ],
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop", "convertible", "tablet", "embedded"]),
            },
            "master": {
                "date-start": "2025-11-14",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "lenovo-a6010": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "microsoft-surface-rt": {
        "branch_configs": {
            "all": {
                # Tablet with detachable keyboard
                "ui": get_ui_list(chassis=["convertible"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "motorola-harpia": {
    },
    "nokia-n900": {
        "branch_configs": {
            "all": {
                "ui": [
                    "console",
                    "i3wm",
                    "sway",
                    "sxmo-de-dwm",
                    "sxmo-de-sway",
                ],
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.06": {
                # Handset with keyboard
                "ui": get_ui_list(chassis=["convertible"], supports_gpu=False),
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "nvidia-tegra-armv7": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["convertible", "tablet", "handset"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "odroid-xu4": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["embedded"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "oneplus-enchilada": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "oneplus-fajita": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "pine64-pinebookpro": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["laptop"], add_ui=["os-installer"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
                "ui": get_ui_list(chassis=["laptop"], add_ui=["os-installer"]),
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "pine64-pinephone": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "pine64-pinephonepro": {
    },
    "pine64-rockpro64": {
        "branch_configs": {
            # Disable plasma bigscreen:
            # https://gitlab.postmarketos.org/postmarketOS/pmaports/-/issues/2650
            "all": {
                "ui": get_ui_list(chassis=["embedded"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "postmarketos-trailblazer": {
        "branches": [
            "master",
            # Decided to not ship it in stable releases
        ],
        "branch_configs": {
            "master": {
                "date-interval": 1,
                "ui": ["gnome", "console", "os-installer"],
                "kernels": [
                    "next",
                ],
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        }
    },
    "purism-librem5": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        }
    },
    "qcom-msm8953": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        }
    },
    "qcom-sm7150": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-a3": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        }
    },
    "samsung-a5": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        }
    },
    "samsung-coreprimevelte": {
        "branch_configs": {
            "all": {
                # Only usable UI at the moment
                "ui": [ "sxmo-de-sway" ],
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-e7": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-espresso10": {
        "branch_configs": {
            "all": {
                "android-recovery-zip": True,
                "ui": get_ui_list(chassis=["tablet"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-espresso7": {
        "branch_configs": {
            "all": {
                "android-recovery-zip": True,
                "ui": get_ui_list(chassis=["tablet"], supports_gpu=False),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-grandmax": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-gt510": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-gt58": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-m0": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-manta": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["tablet"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-serranove": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "samsung-starqltechn": {
        "branches": [
            "master",
            "v25.12",
        ],
        "branch_configs": {
            "master": {
                "date-start": "2025-08-08",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "shift-axolotl": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "wileyfox-crackling": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
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
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "xiaomi-elish": {
        "branch_configs": {
            "all": {
                "kernels": [
                    "boe",
                    "csot",
                ],
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "xiaomi-nabu": {
        "branch_configs": {
            "all": {
                "ui": get_ui_list(chassis=["convertible", "handset"]),
            },
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.06": {
                "ui": get_ui_list(),
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "xiaomi-scorpio": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
    "xiaomi-wt88047": {
        "branch_configs": {
            "master": {
                "date-start": "2025-01-10",  # Friday
            },
            "v25.12": {
                "date-start": "2025-12-15",  # Monday
            },
        },
    },
}
