import discord
from discord.ext import commands
import json
import os

# Initialize Bot object (inherits from Client)
prefix = '!'
bot = commands.Bot(command_prefix=prefix)
bot.remove_command('help')


# Function to generate the `info.json` file
def generateInfo(groupName):
    pass


if __name__ == "__main__":

    # Get the group name
    groupName = input("What is the group name?\n")
    bot.info["groupName"] = groupName

    # If there is no `info.json` already, generate one
    path = f"./groups/{groupName}/info.json"
    if not os.path.isfile(path):
        generateInfo(path)

    # Used to create the `!help` command
    bot.helpInfo = {}

    # Load the twitter stuff and save it to the `bot` object
    bot.info = {}
    twitterStuffString = open("./twitterStuff.txt").read()
    bot.info["twitter"] = json.loads(twitterStuffString)

    # Load the different roles in the `bot` object
    with open(path, "r") as f:
        info = json.load(f)
        f.close()
    bot.info["owners"] = info["owners"]
    bot.info["admins"] = info["admins"]

    # Load the cogs
    for cog in info["cogs"]:
        bot.load_extension(f"cogs.{cog}")

    # Start the bot
    discordToken = open(f"./groups/{groupName}/discordToken.txt").read()
    bot.run(discordToken)
