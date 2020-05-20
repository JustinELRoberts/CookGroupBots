from discord.ext import commands
import discord
import twitter
import json
import math
import re
import os


# Discord server settings
DISCORD_BOT_ID = 650713254322241559
DISCORD_SUCCESS_CHANNEL_ID = 712657003109023766
DISCORD_SHOP_CHANNELS = [711960475340111943]
DISCORD_ADMINS = [553221161450733569]

# UI settings
successPoints = 10
itemsPerPage = 5
groupName = "Justin Notify"

# Colors used for embeds
greenHex = 0x00ff00
yellowHex = 0xfbde67
redHex = 0xff0000
shopHex = 0x00ff00

# Initialize Bot object (inherits from Client)
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')

# Regex matching patterns
hyperlink_url_pattern = re.compile(r"\((.+)\)")
tweet_id_pattern = re.compile(r"/status/(\d+)")

# Used for adding reactions for shop page navigation
numberEmojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣',
                '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


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


# Get the linked jump url from the embed's added field
def get_linked_jump_url(embed):
    for field in embed.fields:
        if field.name == "Your Post":
            jump_url = hyperlink_url_pattern.search(field.value).group(1)
            return jump_url
    return None


# Generate and return the fields for a certain page for the shop
def generatePageFields(page):
    fields = []
    indices = [(page - 1) * itemsPerPage, page * itemsPerPage]
    items = list(shop.items())[indices[0]:indices[1]]
    for item in sorted(items, key=lambda item: item[1]["Points"]):
        name = item[0]
        points = item[1]["Points"]
        stock = item[1]["Stock"]
        fields.append({"name": f"**{name}**",
                       "value": f"Cost: {points} points\nStock: {stock}",
                       "inline": False})
    return fields


# Helper function to unpack a rawReactionActionEvent
# Returns a dict containing useful information about the reaction
async def unpackRawReactionActionEvent(reactionEvent):
    authorID = reactionEvent.user_id
    user = bot.get_user(authorID)
    channel = bot.get_channel(reactionEvent.channel_id)
    message = await channel.fetch_message(reactionEvent.message_id)
    return (authorID, user, channel, message)


# Function used to add functionality for post deletion when reating
# to a post
async def deleteSuccess(rawReactionActionEvent):

    # Unpack the rawReactionActionEvent
    e = rawReactionActionEvent
    authorID, user, channel, message = await unpackRawReactionActionEvent(e)

    # If this is not sent from the proper channel, stop here
    if channel.id != DISCORD_SUCCESS_CHANNEL_ID:
        return

    # If the reaction was sent by us, stop here
    if user.id == DISCORD_BOT_ID:
        return

    # If the reaction isnt ❌, stop here
    if rawReactionActionEvent.emoji.name != '❌':
        return

    # If the reaction is not sent by the message author, delete it
    for reaction in message.reactions:
        if user.id != message.author.id:
            await reaction.remove(user)
            return

    # If we get to this point, we need to delete all associated posts
    # First we need to get the post we made in response to the OP
    async for post in message.channel.history(after=message.created_at):
        jump_url = get_linked_jump_url(post.embeds[0])
        # Once we find the message, delete the tweet, user post, and bot post
        if jump_url == message.jump_url:
            tweet_url = get_tweet_url(post.embeds[0])
            delete_tweet(tweet_url)
            await post.delete()
            await message.delete()
            addPoints(authorID, -successPoints)
            await send_embed(message.channel, f"{message.author}",
                             "Your success has been deleted from Twitter.\n" +
                             f"You have {getPoints(authorID)} points.\n",
                             redHex)


# Function to edit a shop post to change pages
async def shopNavigation(rawReactionActionEvent):

    # Unpack the rawReactionActionEvent
    e = rawReactionActionEvent
    authorID, user, channel, message = await unpackRawReactionActionEvent(e)
    author = bot.get_user(authorID)
    emoji = rawReactionActionEvent.emoji

    # If this is not sent from the proper channel, stop here
    if channel.id not in DISCORD_SHOP_CHANNELS:
        return

    # If the reaction was sent by us, stop here
    if user.id == DISCORD_BOT_ID:
        return

    # If the message itself is not one of the shop messages, stop here
    if len(message.embeds) != 1:
        return
    embed = message.embeds[0]
    if f"**{groupName} Shop Page" not in embed.description:
        return

    # If the reaction isnt a number emoji, remove it and stop here
    if emoji.name not in numberEmojis:
        await message.remove_reaction(emoji, author)
        return

    # If we get to this point, we need change shop pages
    pageNum = numberEmojis.index(emoji.name) + 1
    fields = generatePageFields(page=pageNum)
    embed = discord.Embed(title="",
                          description=f"🎁 **{groupName} Shop Page 1** 🎁",
                          color=shopHex)
    for field in fields:
        embed.add_field(name=field["name"], value=field["value"],
                        inline=field["inline"])
    await message.edit(embed=embed)

    # Remove the reaction
    await message.remove_reaction(emoji, author)


# Function to respond to success posts
async def respondToSuccess(message):

    # Otherwise iterate through all the images sent and post them to twitter
    msgLink = message.jump_url
    isAttached = False
    fields = []
    for attachment in message.attachments:
        isAttached = True
        tweetURL = post_tweet(attachment.url, message.author)
        addPoints(message.author.id)
        fields.append({"name": "Your Post", "value": f"[Here]({msgLink})",
                      "inline": True})
        fields.append({"name": "Tweet", "value": f"[Here]({tweetURL})",
                      "inline": True})

    # If the message sent was an image link, post it to twitter
    for ext in mediaExt:
        if message.content.endswith(ext):
            isAttached = True
            tweetURL = post_tweet(message. content, message.author)
            addPoints(message.author.id)
            fields.append({"name": "Your Post", "value": f"[Here]({msgLink})",
                          "inline": True})
            fields.append({"name": "Tweet", "value": f"[Here]({tweetURL})",
                          "inline": True})

    if isAttached:
        await send_embed(message.channel, "Success!",
                         "Your success has been post to Twitter. " +
                         f"You have {getPoints(message.author.id)} points.\n" +
                         "Please react with ❌ if you'd like to " +
                         "remove the post", greenHex, fields)
        await message.add_reaction('❌')
    else:
        await send_embed(message.channel, "Error", "Please make sure you " +
                         "include an image or video in your post.", redHex)


# --------------------------------------------------------------------------- #
# ----------------------------- Twitter Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# Get the linked tweet url from the embed's added field
def get_tweet_url(embed):
    for field in embed.fields:
        if field.name == "Tweet":
            tweet_url = hyperlink_url_pattern.search(field.value).group(1)
            return tweet_url
    return None


# Post an image to twitter from a link
def post_tweet(url, discordName):

    # Login to twitter
    api = twitter.Api(consumer_key=twitterStuff["key"],
                      consumer_secret=twitterStuff["secret"],
                      access_token_key=twitterStuff["token"],
                      access_token_secret=twitterStuff["tokenSecret"],
                      sleep_on_rate_limit=True)

    # Tweet the image/video
    statusObj = api.PostUpdate(status=f"Success from {discordName}", media=url)

    return statusObj.media[0].expanded_url


# Delete a tweet, given its url
def delete_tweet(tweet_url):

    # Login to twitter
    api = twitter.Api(consumer_key=twitterStuff["key"],
                      consumer_secret=twitterStuff["secret"],
                      access_token_key=twitterStuff["token"],
                      access_token_secret=twitterStuff["tokenSecret"],
                      sleep_on_rate_limit=True)

    # Get the tweet's id
    tweet_id = tweet_id_pattern.search(tweet_url).group(1)

    # Delete the post
    api.DestroyStatus(tweet_id)


# --------------------------------------------------------------------------- #
# ------------------------- Data Management Funcs --------------------------- #
# --------------------------------------------------------------------------- #
# ------------------------ General Data Management -------------------------- #
# Function to load the current point dict
def loadData(dataType):

    # Return an empty dict if we havent stored anything yet
    if not os.path.exists(f"./{dataType}.json"):
        return {}

    # If we have, load it and return the result
    with open(f"./{dataType}.json", 'r') as f:
        loadedData = json.load(f)
        f.close()
    return loadedData


# Function to save the current point dict
def saveData(dataType, data):
    with open(f"./{dataType}.json", 'w+') as f:
        json.dump(data, f)
        f.close


# --------------------------- Point Management ------------------------------ #
# Function to add points to the user who's discordID is `id`
# By default, adds `successPoints` points
def addPoints(id, amount=successPoints):
    id = str(id)
    if id not in points.keys():
        points[id] = amount
    else:
        points[id] += amount
    saveData("points", points)


# Funtion which returns the number of points for a given user
def getPoints(id):
    id = str(id)
    return points[id]


# --------------------------------------------------------------------------- #
# --------------------------------- Events ---------------------------------- #
# --------------------------------------------------------------------------- #
# ---------------------------- on_message Event ----------------------------- #
mediaExt = ['.jpg', '.png', '.jpeg', '.mp4']
@bot.event
async def on_message(message):

    # If the bot sent this message, stop here
    if message.author.id == DISCORD_BOT_ID:
        return

    # If this sent from success, repond to it
    if message.channel.id == DISCORD_SUCCESS_CHANNEL_ID:
        await respondToSuccess(message)

    # Otherwise process commands
    await bot.process_commands(message)


# -------------------------  on_reaction_add Event -------------------------- #
@bot.event
async def on_raw_reaction_add(rawReactionActionEvent):

    await deleteSuccess(rawReactionActionEvent)
    await shopNavigation(rawReactionActionEvent)


# --------------------------------------------------------------------------- #
# ------------------------------ User Commands ------------------------------ #
# --------------------------------------------------------------------------- #
# ------------------------------ Shop Command ------------------------------- #
@bot.command(name='shop')
@commands.cooldown(1, 0.5, commands.BucketType.user)
async def shop(ctx):

    # If this isn't one of the channels where we take commands, stop here
    if ctx.channel.id not in DISCORD_SHOP_CHANNELS:
        return

    # If the shop is empty, alert the user
    if len(shop) == 0:
        await send_embed(ctx, "__Shop Page 1__",
                         "The shop is empty 😔",
                         shopHex)
        return

    # Otherwise display the shop's first page, containing `itemsPerPage` items
    fields = generatePageFields(page=1)
    message = await send_embed(ctx, "", f"🎁 **{groupName} Shop Page 1** 🎁",
                               shopHex, fields)

    # Add reactions for page navigation
    numPages = math.ceil(len(shop.keys()) / itemsPerPage)
    for num in range(numPages):
        await message.add_reaction(numberEmojis[num])


# --------------------------------------------------------------------------- #
# ------------------------------ Admin Commands ----------------------------- #
# --------------------------------------------------------------------------- #
async def isValidCall(ctx, commandInfo, args, extraArgs):

    # Usage string
    usage = "Usage:"
    for command in commandInfo["args"]:
        usage += f" <{command}>"

    # If we are not in a DM, stop here
    if (not isinstance(ctx.channel, discord.DMChannel)):
        return False

    # If an admin did not send this message, stop here
    if ctx.author.id not in DISCORD_ADMINS:
        return False

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
        await send_embed(ctx.channel, "Error",
                         "One or more argument(s) are of the wrong type.\n" +
                         "Usage: `!add <productName> <cost> <stock>`\n" +
                         "where <productName> is a string, <cost> is an" +
                         "integer, and <stock> is an integer.", redHex)
        return False

    # If we get to this point, the command is valid
    return True


# ---------------------------- Add product stock  --------------------------- #
@bot.command(name='add')
@commands.cooldown(1, 0.5, commands.BucketType.user)
async def add(ctx, productName=None, cost=None, stock=None, *args):

    # If this isn't a valid call of this function, stop here
    commandInfo = {"name": "add",
                   "args": {"productName": str, "cost": int, "stock": int}}
    isValid = await isValidCall(ctx, commandInfo,
                                [productName, cost, stock], args)
    if not isValid:
        return


# -------------------------------- Enter Here ------------------------------- #
# Start the bot
if __name__ == "__main__":

    # Load the stored points and shop
    points = loadData("points")
    shop = loadData("shop")

    # Load twitter stuff
    twitterStuffString = open("./twitterStuff.txt").read()
    twitterStuff = json.loads(twitterStuffString)

    # Start the bot
    discordToken = open("./discordToken.txt").read()
    bot.run(discordToken)
