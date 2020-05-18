from discord.ext import commands
import discord
import twitter
import json
import math
import re
import os


# UI settings for a particular group
successPoints = 10
itemsPerPage = 5
groupName = "Justin Notify"

# Discord server settings
DISCORD_BOT_ID = 650713254322241559
DISCORD_SUCCESS_CHANNEL_ID = 710479705798869143
DISCORD_COMMANDS_CHANNELS = [711960475340111943]

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


# Function used to add functionality for post deletion when reating
# to a post
async def deleteSuccess(rawReactionActionEvent):

    # Get the channel and message this react occured in
    authorID = rawReactionActionEvent.user_id
    user = bot.get_user(authorID)
    channel = bot.get_channel(rawReactionActionEvent.channel_id)
    message = await channel.fetch_message(rawReactionActionEvent.message_id)

    # If this is not sent from the proper channel, stop here
    if channel.id != DISCORD_SUCCESS_CHANNEL_ID:
        return

    # If the reaction was sent by us, return
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


# Function to edit a shop post to change pages
def shopNavigation(rawReactionActionEvent):
    pass


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
# -------------------------------- Commands --------------------------------- #
# --------------------------------------------------------------------------- #
# ------------------------------ Shop Command ------------------------------- #
@bot.command(name='shop')
@commands.cooldown(1, 0.5, commands.BucketType.user)
async def shop(ctx):

    # If this isn't one of the channels where we take commands, stop here
    if ctx.channel.id not in DISCORD_COMMANDS_CHANNELS:
        return

    # If the shop is empty, alert the user
    if len(shop) == 0:
        await send_embed(ctx, "__Shop Page 1__",
                         "The shop is empty 😔",
                         shopHex)
        return

    # Otherwise display the shop's first page, containing `itemsPerPage` items
    fields = []
    for num, item in enumerate(sorted(shop.items(),
                                      key=lambda item: item[1]["Points"])):
        if num >= itemsPerPage:
            break

        name = item[0]
        points = item[1]["Points"]
        stock = item[1]["Stock"]
        fields.append({"name": f"**{name}**",
                       "value": f"Cost: {points} points\nStock: {stock}",
                       "inline": False})

    message = await send_embed(ctx, "", f"🎁 **{groupName} Shop Page 1** 🎁",
                               shopHex, fields)

    # Add reactions for page navigation
    numPages = math.ceil(len(shop.keys()) / itemsPerPage)
    for num in range(numPages):
        await message.add_reaction(numberEmojis[num])

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
