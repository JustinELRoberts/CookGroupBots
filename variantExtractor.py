from discord.ext import commands
import discord
import requests
import re

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


# Function which returns a dict whosekeys are sizes and values are variants
def getVariants(url):

    # Match the url
    match = urlPattern.match(productURL)
    if match is None:
        return None

    # Make a GET request to the stock endpoint for this item
    stockEndpoint = productURL + '.json'
    print(stockEndpoint)
    res = requests.get(stockEndpoint).json()
    if not res:
        return None

    # Parse and return the relevant data
    result = {}
    result["title"] = res["product"]["title"]
    result["pid"] = res["product"]["id"]
    result["variants"] = {}
    variants = res["product"]["variants"]
    for variant in variants:
        result["variants"][variant["title"]] = variant["id"]

    return result


if __name__ == "__main__":
    productURL = "https://www.dtlr.com/products/jordan-air-jordan-retro-1-high-og-royal-toe-555088-041"
    print(getVariants(productURL))
