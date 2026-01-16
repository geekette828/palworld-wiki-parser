This project includes a full, vendored version of Pywikibot inside the pwb/ folder. <br>
There’s no need to install it separately or use it as a submodule.

    💡 All Pywikibot commands should be run through the included pwb.ps1 launcher to ensure the correct environment is used.

Update `pwb\user-config.py.sample` to `pwb\user-config.py`<br>
Replace `YourUsernameHere` with your wiki.gg username.

Update `pwb\user-password.py.sample` to `pwb\user-password.py`<br>
Replace `YourUserNameHere` with your wiki.gg username.<br>
Replace `YourBotNameHere` with the name you gave it in the `Special:ApplicationPasswords` page<br>
Replace `YourBotPasswordHere` with the long unique hash for that specific bot name, that the wiki gave you.

    🚨🔐 DO NOT SHARE THIS PASSWORD WITH ANYONE. 🔐🚨

Login to pywikibot useing the command:<br>
`.\pwb.ps1 login`

This means running any of the pywikibot parser scripts needs to have the full path.<br>
`.\pwb.ps1 "U:\R-PATH\Sun Haven Parser\pywikibot_tools\compare_recipe.py"`