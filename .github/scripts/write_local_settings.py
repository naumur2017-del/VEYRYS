"""Generate veyrys_shop/local_settings.py from deploy-time environment secrets.

Run only inside the GitHub Actions deploy job, right before pushing to the
Gandi deployment mirror. The resulting file is never pushed to GitHub itself.
"""

import os

SECRET_NAMES = [
    "ADMIN_ORDER_EMAIL",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "CAMERPAY_API_TOKEN",
    "CAMERPAY_CALLBACK_SECRET",
]


def main():
    lines = [
        "# Generated at deploy time by GitHub Actions from environment secrets.\n",
        "# Not part of GitHub history; only pushed to the Gandi deployment mirror.\n",
    ]
    for name in SECRET_NAMES:
        value = os.environ.get(name, "")
        if value:
            lines.append(f"{name} = {value!r}\n")

    with open("veyrys_shop/local_settings.py", "w") as f:
        f.writelines(lines)


if __name__ == "__main__":
    main()
