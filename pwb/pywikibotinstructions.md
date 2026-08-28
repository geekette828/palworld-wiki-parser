This project includes a full, vendored version of Pywikibot inside the pwb/ folder. <br>
There’s no need to install it separately or use it as a submodule.

    💡 All Pywikibot commands should be run through the included launcher to ensure the correct
    environment is used. Use `pwb.ps1` on Windows (PowerShell) and `pwb.sh` on Linux/macOS.
    Both resolve their own location, so the repo can live in any directory.

Update `pwb\user-config.py.sample` to `pwb\user-config.py`<br>
Replace `YourUsernameHere` with your wiki.gg username.

Update `pwb\user-password.py.sample` to `pwb\user-password.py`<br>
Replace `YourUserNameHere` with your wiki.gg username.<br>
Replace `YourBotNameHere` with the name you gave it in the `Special:ApplicationPasswords` page<br>
Replace `YourBotPasswordHere` with the long unique hash for that specific bot name, that the wiki gave you.

    🚨🔐 DO NOT SHARE THIS PASSWORD WITH ANYONE. 🔐🚨

Login to pywikibot useing the command:<br>
Windows: `.\pwb.ps1 login`<br>
Linux/macOS: `./pwb.sh login`

This means running any of the pywikibot parser scripts needs to have the full path.<br>
Windows: `.\pwb.ps1 "N:\R-PATH\Palworld Parser\pywikibot_tools\compare_pages\compare_page_pal.py"`<br>
Linux/macOS: `./pwb.sh "/path/to/palworld-wiki-parser/pywikibot_tools/compare_pages/compare_page_pal.py"`