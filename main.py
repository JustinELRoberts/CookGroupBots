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
    bot.groupName = groupName

    # If there is no `info.json` already, generate one
    if not os.path.isfile(f"./groups/{groupName/info.json}"):
        generateInfo(groupName)

    # Load the cogs
    with open(f"./groups/{groupName}/info.json", "r") as f:
        info = json.load(f)
        f.close()
    for cog in info["cogs"]:
        bot.load_extension(f"cogs.{cog}")

    # Start the bot
    discordToken = open(f"./groups/{groupName}/discordToken.txt").read()
    bot.run(discordToken)
