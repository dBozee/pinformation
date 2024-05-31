# pinformation
A simple discord bot that allows you to keep messages pinned to the bottom of a channel.

## Getting Started

The bot is available in two flavors. Local deployment and Docker.
Clone this repo into the location of your choosing before continuing.

### Running the bot locally
To run the bot locally, you will need to have [Poetry](https://python-poetry.org/) installed.
Currently, you will need to configure the bot locally prior to deploying either way.

1. navigate to the root /pinformation/ directory
1. run `poetry install --no-dev`
    - This should install all required dependencies
1. deploy the bot by running `poetry run python pinformation_bot`
1. verify the bot is running by checking in discord. The bot should now show online. You can try running `/botinfo` and should get an ephemeral embed response showing info on the bot.
    - the `pin_cache.db` file in the volume will be generated by the script on its first run.


### Running the bot in Docker
1. navigate to the root /pinformation/ directory
1. configure the bot by modifying the `config/config.json` file. You'll need to add at least your 
own discord ID or role ID to the list of permitted users before deploying the bot. Additional users/roles can be added using slash commands later.
    - **Reminder:** the IDs have to be stored as strings **NOT** ints. This is a json limitation with int sizes.

1. run `docker build -t pinformation .` and wait for the build to complete
1. run docker run with your discord token and the path to the config.json on your local(host) machine:
    ```sh
    docker run -d -e DISCORD_TOKEN="YOUR_TOKEN_HERE" -v "/path/to/host/config:/app/config" --restart unless-stopped pinformation
    ```
    - this step will copy the existing `config.json` file on your host machine to the /config/ folder in our container
    so ensure you did not skip step 2 before building/deploying
    - If you have an existing `pin_cache.db` file, it will also be copied. If not, don't worry, the script will generate a new one when it runs for the first time and it will be added to the Docker volume
1. verify the bot is running by checking in discord. The bot should now show online. You can try running `/botinfo` and should get an ephemeral embed response showing info on the bot.
    - if the bot is showing offline, check the docker container logs for more info.
    - the `pin_cache.db` file in the volume will be generated by the script on its first run.

## Commands

The bot currently offers two sets of [cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html); management and pins. All commands have a slash(/) command option available, however, you can also set the prefix in the config.json file.
- The management cog contains all commands pertaining to managing the bot and user permissions around the bot.
- The pins cog contains all commands pertaining to starting, stopping, tracking and updating the pins.

### Management commands

The only management command which doesn not require management permissions is `/botinfo`

- **botinfo**
    - Get information about the bot.

- **manageuser**
    - Add or remove a user from the bot permissions list.
    - Management perms required
    - params:
        - user_id: The id of the user to be added
        - action: add or remove(literal)

- **managerole**
    - Add or remove a role from the bot permissions list.
    - Management perms required
    - params:
        - role_id: The id of the user to be added
        - action: add or remove(literal)

- **reload**
    - Reloads the running cogs for debugging purposes.
    - Management perms required

- **shutdown**
    - Shut down the bot.
    - Management perms required
    - **WARNING!** - Using this command(currently) in the docker deployment will require you to start the container again.


### Pins

All pin commands require management permissions to run.

- **pintext**
    - Pin plain text to a channel. Supports emojis and hyperlinks.
    - params:
        - text: The text to be pinned

- **pinembed**
    - Pin an embed to a channel.
    - params:
        - title: The title to show at the top of the embed. Support emojis, hyperlinks, etc.
        - text: the body of the embed. Supports emojis, hyperlinks, etc.
        - url: The URL that the title can link to. Optional.
        - image: The image to be displayed along with the embed. Optional.
        - color: The color of the embed in decimal format. Optional. Default is set in config.json

- **pinstop**
    - Stop the pin in the current channel. undo with /pinrestart

- **pinrestart**
    - Restart the last active pin in the current channel.

- **pinspeed**
    - Set the speed of the pin in the current channel to a certain number of messages. 
    Requires an active pin.
    - params:
        - speed(int)

- **allpins**
    - get a list of all active pins in this guild.