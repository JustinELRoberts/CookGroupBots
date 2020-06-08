from discord.ext import commands
import discord
import requests
import json
import os
import re

# Colors used for embeds
greenHex = 0x00ff00
yellowHex = 0xfbde67
redHex = 0xff0000
shopHex = 0x00ff00

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
async def send_embed(ctx, title, desc, color, fields=None):
    embed = discord.Embed(title=title, description=desc, color=color)
    if fields is not None:
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"],
                            inline=field["inline"])
    return await ctx.send(embed=embed)


# --------------------------------------------------------------------------- #
# ----------------------------- Request Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# Function which returns a dict whose keys are sizes and values are vars
def getVariants(url):

    # Match the url
    match = urlPattern.match(url)
    if match is None:
        return None

    # Make a GET request to the stock endpoint for this item
    stockEndpoint = url + '.json'
    res = requests.get(stockEndpoint).json()
    if not res:
        return None

    # Parse and return the relevant data
    result = {}
    result["title"] = res["product"]["title"]
    result["variants"] = {}
    variants = res["product"]["variants"]
    for variant in variants:
        result["variants"][variant["title"]] = variant["id"]

    return result


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# -------------------------- VariantExtractor Cog --------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
class VariantExtractor(commands.Cog):

    # ----------------------------------------------------------------------- #
    # ---------------------------- Initialization --------------------------- #
    # ----------------------------------------------------------------------- #
    def __init__(self, bot):
        self.bot = bot

        bot.tempTest = "ahhhh"

        # Load group settings
        relPath = f"../groups/{self.bot.groupName}/info.json"
        myPath = os.path.abspath(os.path.dirname(__file__))
        absPath = os.path.join(myPath, relPath)
        with open(absPath, "r") as f:
            info = json.load(f)
            f.close()
        self.id = int(info["botID"])
        self.allowedChannels = []
        for channel in info["variantExtractor"]["channels"]:
            self.allowedChannels.append(int(channel))

    # ----------------------------------------------------------------------- #
    # ------------------------------- Commands ------------------------------ #
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    # ---------- Helper function to validate the call of a command ---------- #
    # ----------------------------------------------------------------------- #
    async def isValidCall(self, ctx, commandInfo, args, extraArgs):

        # Usage string
        usage = f"Usage: `{self.bot.command_prefix}{commandInfo['name']}"
        for command in commandInfo["args"]:
            usage += f" <{command}>"
        usage += "`"

        # If we aren't in one of the variant channels, stop here
        if ctx.channel.id not in self.allowedChannels:
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

    # ----------------------------------------------------------------------- #
    # ----------------------------- !variants ------------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name="variants")
    async def variants(self, ctx, url=None, *args):

        # If this isn't a valid call of this command, stop here
        commandInfo = {"name": "variants", "args": {"url": str}}
        isValid = await self.isValidCall(ctx, commandInfo, [url], args)
        if not isValid:
            return

        # Get the variants and alert the user of the result
        variants = getVariants(url)
        if variants is None:
            await send_embed(ctx, "Error", "We could not find variants for " +
                             "the product you linked.", redHex)
            return
        else:
            description = ""
            for variant in variants["variants"]:
                description += f"{variant} - {variants['variants'][variant]}\n"
            await send_embed(ctx, f"__{variants['title']}__",
                             description, greenHex)


# --------------------------------------------------------------------------- #
# ----------------------------- Initialize Cog ------------------------------ #
# --------------------------------------------------------------------------- #
def setup(bot):
    bot.add_cog(VariantExtractor(bot))
