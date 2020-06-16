from discord.ext import commands
import discord
import requests
import json
import re

# TODO: Testing and make this a cog

# Colors used for embeds
greenHex = 0x00ff00
yellowHex = 0xfbde67
redHex = 0xff0000
shopHex = 0x00ff00

# Initialize Bot object (inherits from Client)
prefix = '!'
bot = commands.Bot(command_prefix=prefix)
bot.remove_command('help')

# URL Matching Pattern
patternString = r"^((http[s]?|ftp):\/)?\/?([^:\/\s]+)" + \
                r"((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(.*)?(#[\w\-]+)?$"
urlPattern = re.compile(patternString)


# --------------------------------------------------------------------------- #
# ------------------------------ Helper Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ----------------------------- Discord Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# Function to send a basic embed
async def send_embed(ctx, title, description, color, fields=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields is not None:
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"],
                            inline=field["inline"])
    return await ctx.send(embed=embed)


# --------------------------------------------------------------------------- #
# ----------------------------- Request Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# Function which views an ebay listing a given number of times
def getViews(url, numViews):

    # Match the url
    match = urlPattern.match(url)
    if match is None:
        return False

    # Make `numViews` GET requests to `url`
    for _ in range(numViews):
        res = requests.get(url)
        if not res:
            return False

    return True


# --------------------------------------------------------------------------- #
# --------------------------------- Commands -------------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ------------ Helper function to validate the call of a command -------------#
# --------------------------------------------------------------------------- #
async def isValidCall(ctx, commandInfo, args, extraArgs,):

    # Usage string
    usage = f"Usage: `{prefix}{commandInfo['name']}"
    for command in commandInfo["args"]:
        usage += f" <{command}>"
    usage += "`"

    # If we aren't in one of the variant channels, stop here
    if ctx.channel.id != DISCORD_EBAY_CHANNEL_ID:
        return

    # Make sure all args were passed
    if None in args:
        description = "You are missing one or more arguments.\n"
        description += usage
        await send_embed(ctx.channel, "Error", description, redHex)
        return False

    # Make sure not too many args are passed
    if len(extraArgs) > 0:
        description = "You sent too many arguments.\n"
        description += usage
        await send_embed(ctx.channel, "Error", description, redHex)
        return False

    # Check that every passed argument is the proper type
    try:
        for argName, argVal in zip(commandInfo["args"], args):
            commandInfo["args"][argName](argVal)
    except ValueError:
        errorMsg = "One or more argument(s) are of the wrong type.\n"
        errorMsg += usage + "\n"
        errorMsg += "where"
        numCommands = len(commandInfo["args"])
        for num, command in enumerate(commandInfo["args"]):
            commandType = commandInfo['args'][command].__name__
            errorMsg += f" `<{command}>` is a `{commandType}`"
            if numCommands > 2:
                errorMsg += ","
            if num == numCommands - 2:
                errorMsg += " and"

        await send_embed(ctx.channel, "Error", errorMsg, redHex)
        return False

    # If we get to this point, the command is valid
    return True


# --------------------------------------------------------------------------- #
# --------------------------------- !view ----------------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='view')
async def view(ctx, url=None, *args):

    # If this isn't a valid call of this command, stop here
    commandInfo = {"name": "view", "args": {"url": str}}
    isValid = await isValidCall(ctx, commandInfo, [url], args)
    if not isValid:
        return

    # Attempt to view the url for the user and alert them of the result
    viewsSuccessful = getViews(url, 20)
    if not viewsSuccessful:
        await send_embed(ctx, "Error", "Unable to view this listing.",
                         redHex)
    else:
        await send_embed(ctx, "Success!", "20 views have been " +
                         "added to your listing", greenHex)


if __name__ == "__main__":

    # Get the group name
    groupName = input("What is the group name?\n")

    # Load group settings
    with open(f"./{groupName}/info.json", "r") as f:
        info = json.load(f)
        f.close()
    DISCORD_BOT_ID = int(info["DISCORD_BOT_ID"])
    DISCORD_EBAY_CHANNEL_ID = int(info["DISCORD_EBAY_CHANNEL_ID"])

    # Start the bot
    discordToken = open(f"./{groupName}/discordToken.txt").read()
    bot.run(discordToken)
