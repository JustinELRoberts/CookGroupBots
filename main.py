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
# Function to load the `info.json` file
def loadInfo(groupName):
    path = f"./groups/{groupName}/info.json"
    with open(path, 'r') as f:
        info = json.load(f)
        f.close()
    return info


# Function to save the `info.json` file
def saveInfo(groupName, info):
    path = f"./groups/{groupName}/info.json"
    with open(path, 'r') as f:
        f.write(json.dumps(info))
        f.close()


# Function to safely cast a variable `var` to the type `varType`
# Prints an error message using `varName` and `varType` if casting fails
def safeCast(var, castInfo):

    # Unpack the input
    varType = castInfo['varType']
    varName = castInfo['varName']
    typeName = castInfo['typeName']

    # Safely cast the value passed
    try:
        var = varType(var)
        return var
    except ValueError:
        print(f"ERROR: {varName} should be {typeName}.")
        return None


# Helper function to accept input in a deterministic way
def getInput(inputInfo):

    # Only used if we require multiple values
    info = []

    # Get the value from the user
    prompt = inputInfo["firstPrompt"]
    userInput = input('\n' + prompt)

    # Parse the input and take more if needed
    while userInput.lower() != "done":
        userInput = safeCast(userInput, inputInfo["castInfo"])

        if userInput is not None:
            if inputInfo["nextPrompt"] is None:
                return userInput
            else:
                info.append(userInput)
                prompt = inputInfo["nextPrompt"]

        userInput = input('\n' + prompt)

    return info


# Function to generate the `info.json` file
def generateInfo():

    # The object to return
    info = {}

    # Get the owners' user IDs
    info["owners"] = getInput({
        "firstPrompt": 'Please type the user ID of one of the owners ' +
                       'followed by the <enter> key.\n',
        "nextPrompt": 'Please type the user ID of another owner ' +
                      'followed by the <enter> key.\n' +
                      'Type "done" when you are finished.\n',
        "castInfo":
        {
            "varType": int,
            "varName": "User IDs",
            "typeName": "integers"
        }
    })

    # Admins can be added using the bot
    info["admins"] = []

    # Get the bot's user ID
    info["botID"] = getInput({
        "firstPrompt": 'Please type the user ID of the Discord bot ' +
                       'followed by the <enter> key.\n',
        "nextPrompt": None,
        "castInfo":
        {
            "varType": int,
            "varName": "User IDs",
            "typeName": "integers"
        }
    })

    return info


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
    path = f"./groups/{groupName}/info.json"
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

    print(generateInfo())

    # # Get the group name
    # # groupName = input("What is your group name?\n")
    # groupName = "justin notify"

    # # If there is no `info.json` already, generate one
    # path = f"./groups/{groupName}/info.json"
    # if not os.path.isfile(path):
    #     bot.info = generateInfo(path)
    # # Otherwise load the pre-exiting data for this group
    # else:
    #     bot.info = loadInfo(groupName)
    #     bot.info["admins"] += bot.info["owners"]
    #     bot.info["groupName"] = groupName

    # # Used to create the `!help` command
    # bot.helpInfo = {}

    # # Load the twitter stuff and save it to the `bot` object
    # twitDir = f"./groups/{groupName}/twitterStuff.txt"
    # twitterStuffString = open(twitDir).read()
    # bot.info["twitter"] = json.loads(twitterStuffString)

    # # Load the cogs
    # for cog in bot.info["cogs"]:
    #     bot.load_extension(f"cogs.{cog}")

    # # Start the bot
    # discordToken = open(f"./groups/{groupName}/discordToken.txt").read()
    # bot.run(discordToken)
