help_pins = [
    {"name": "Pintext", "value": "• Pin plain text to a channel. Supports emojis and hyperlinks."},
    {
        "name": "pinembed",
        "value": (
            "• Pin an embed to a channel.\n"
            "• *unfortunately, discord does not support multiline command arguments for slash commands.*\n"
            'To use multiline, use the prefix command: <prefix>pinembed "text"'
        ),
    },
    {"name": "pinstop", "value": "• Stop the pin in the current channel. undo with /pinrestart"},
    {"name": "pinrestart", "value": "• Restart the last active pin in the current channel."},
    {
        "name": "pinspeed",
        "value": (
            "• Set the speed of the pin in the current channel to a certain number of messages.Requires an active pin."
        ),
    },
    {"name": "allpins", "value": "• get a list of all active pins in this guild."},
]
help_management = [
    {"name": "botinfo", "value": "• Get information about the bot."},
    {"name": "manageuser", "value": "• Add or remove a user from the bot permissions list."},
    {"name": "managerole", "value": "• Add or remove a role from the bot permissions list."},
]
