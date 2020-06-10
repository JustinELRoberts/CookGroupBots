from sharedFuncs import send_embed
import discord
from discord.ext import commands
import json
import os

# Initialize Bot object (inherits from Client)
prefix = '!'
bot = commands.Bot(command_prefix=prefix)
bot.remove_command('help')

# Colors used for embeds
greenHex = 0x00ff00
yellowHex = 0xfbde67
redHex = 0xff0000
shopHex = 0x00ff00


# --------------------------------------------------------------------------- #
# ------------------------------ Helper Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# Function to generate the `info.json` file
def generateInfo(groupName):
    pass


# Function to generate a single command's !help result
def generateHelp(commandName, commandInfo):
    result = f"__**!{commandName}**__\n"
    result += f"**Usage:** `!{commandName}"
    for arg in commandInfo['args']:
        result += f" <{arg}>"
    result += "`\n"
    result += f"**Description:** {commandInfo['description']}\n"
    result += f"**Example:** `{commandInfo['example']}`\n\n"

    return result


# --------------------------------------------------------------------------- #
# -------------------------------- Commands --------------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ------------------------------- !adminadd --------------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name="adminadd")
async def adminadd(ctx):
    pass


# --------------------------------------------------------------------------- #
# --------------------------------- !help ----------------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name="help")
async def help(ctx):

    # Used for the titles of cogs
    commandNames = {
        "twitterSuccessPoints": "Shop",
        "variantExtractor": "Variant Extractor",
        "ebayViewWatcher": "Ebay View Adder"
    }

    # Get the available channels
    with open(path, "r") as f:
        info = json.load(f)
        f.close()

    # If we arent in one of the cogs' channels, do nothing
    channels = []
    currCog = None
    for cog in info["cogs"]:
        channels += info[cog]["channels"]
        if ctx.channel.id in info[cog]["channels"]:
            currCog = cog
    if currCog is None:
        return

    # Return the help menu for this particular cog
    helpInfo = bot.helpInfo[currCog]
    description = ""
    if "owner" in helpInfo and ctx.author.id in bot.info["owner"]:
        for command in helpInfo["owner"]:
            description += generateHelp(command, helpInfo["owner"][command])
        await send_embed(ctx,
                         f"__**{commandNames[currCog]} Owner Commands**__",
                         description, greenHex)

    description = ""
    if "admin" in helpInfo and ctx.author.id in bot.info["admins"]:
        for command in helpInfo["admin"]:
            description += generateHelp(command, helpInfo["admin"][command])
        await send_embed(ctx,
                         f"__**{commandNames[currCog]} Admin Commands**__",
                         description, greenHex)

    description = ""
    if "user" in helpInfo:
        for command in helpInfo["user"]:
            description += generateHelp(command, helpInfo["user"][command])
        await send_embed(ctx,
                         f"__**{commandNames[currCog]} Commands**__",
                         description, greenHex)


if __name__ == "__main__":

    # Used to share information between cogs
    bot.info = {}

    # Get the group name
    # groupName = input("What is the group name?\n")
    groupName = "justin notify"
    bot.info["groupName"] = groupName

    # If there is no `info.json` already, generate one
    path = f"./groups/{groupName}/info.json"
    if not os.path.isfile(path):
        generateInfo(path)

    # Used to create the `!help` command
    bot.helpInfo = {}

    # Load the twitter stuff and save it to the `bot` object
    twitDir = f"./groups/{groupName}/twitterStuff.txt"
    twitterStuffString = open(twitDir).read()
    bot.info["twitter"] = json.loads(twitterStuffString)

    # Load the different roles in the `bot` object
    with open(path, "r") as f:
        info = json.load(f)
        f.close()
    bot.info["owners"] = info["owners"]
    bot.info["admins"] = info["admins"]
    bot.info["admins"] += bot.info["owners"]

    # Load the cogs
    for cog in info["cogs"]:
        bot.load_extension(f"cogs.{cog}")

    # Start the bot
    discordToken = open(f"./groups/{groupName}/discordToken.txt").read()
    bot.run(discordToken)
