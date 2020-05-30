from discord.ext import commands
import discord
import twitter
import json
import math
import re
import os


# Discord server settings
# DISCORD_BOT_ID = 650713254322241559
# DISCORD_SUCCESS_CHANNEL_ID = 712657003109023766
# DISCORD_SHOP_CHANNELS = [711960475340111943]
# DISCORD_ADMINS = [553221161450733569]

# UI settings
successPoints = 10
itemsPerPage = 5

# Colors used for embeds
greenHex = 0x00ff00
yellowHex = 0xfbde67
redHex = 0xff0000
shopHex = 0x00ff00

# Initialize Bot object (inherits from Client)
prefix = '!'
bot = commands.Bot(command_prefix=prefix)
bot.remove_command('help')

# Regex matching patterns
hyperlinkUrlPattern = re.compile(r"\((.+)\)")
tweetIdPattern = re.compile(r"/status/(\d+)")
userMentionPattern = re.compile(r"<@!(\d+)>")

# Used for adding reactions for shop page navigation
numberEmojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣',
                '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


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


# --------------------------------------------------------------------------- #
# ----------------------------- Twitter Funcs ------------------------------- #
# --------------------------------------------------------------------------- #
# Get the linked tweet url from the embed's added field
def get_tweet_url(embed):
    for field in embed.fields:
        if field.name == "Tweet":
            tweet_url = hyperlinkUrlPattern.search(field.value).group(1)
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
    tweetID = tweetIdPattern.search(tweet_url).group(1)

    # Delete the post
    api.DestroyStatus(tweetID)


# --------------------------------------------------------------------------- #
# ------------------------- Data Management Funcs --------------------------- #
# --------------------------------------------------------------------------- #
# ------------------------ General Data Management -------------------------- #
# Function to load the current point dict
def loadData(dataType):

    # Return an empty dict if we havent stored anything yet
    if not os.path.exists(f"./{groupName}/{dataType}.json"):
        return {}

    # If we have, load it and return the result
    with open(f"./{groupName}/{dataType}.json", 'r') as f:
        loadedData = json.load(f)
        f.close()
    return loadedData


# Function to save the current point dict
def saveData(dataType, data):
    with open(f"./{groupName}/{dataType}.json", 'w+') as f:
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
# --------------------------------------------------------------------------- #
# ---------------------------- on_message Event ----------------------------- #
# --------------------------------------------------------------------------- #
# Get the linked jump url from the embed's added field
def get_linked_jump_url(embed):
    for field in embed.fields:
        if field.name == "Your Post":
            jumpURL = hyperlinkUrlPattern.search(field.value).group(1)
            return jumpURL
    return None


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


# --------------------------------------------------------------------------- #
# -------------------------  on_reaction_add Event -------------------------- #
# --------------------------------------------------------------------------- #
# Helper function to unpack a rawReactionActionEvent
# Returns a dict containing useful information about the reaction
async def unpackRawReactionActionEvent(reactionEvent):
    authorID = reactionEvent.user_id
    user = bot.get_user(authorID)
    channel = bot.get_channel(reactionEvent.channel_id)
    message = await channel.fetch_message(reactionEvent.message_id)
    return (authorID, user, channel, message)


# Function used to add functionality for post deletion when reacting
# to a post
async def deleteSuccess(authorID, user, channel, message, event):

    # If this is not sent from the proper channel, stop here
    if channel.id != DISCORD_SUCCESS_CHANNEL_ID:
        return

    # If the reaction was sent by us, stop here
    if user.id == DISCORD_BOT_ID:
        return

    # If the reaction isnt ❌, stop here
    if event.emoji.name != '❌':
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
async def shopNavigation(authorID, user, channel, message, event):

    # Get additional info
    author = bot.get_user(authorID)
    emoji = event.emoji

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


@bot.event
async def on_raw_reaction_add(rawReactionActionEvent):
    e = rawReactionActionEvent
    authorID, user, channel, message = await unpackRawReactionActionEvent(e)
    await deleteSuccess(authorID, user, channel, message,
                        rawReactionActionEvent)
    await shopNavigation(authorID, user, channel, message,
                         rawReactionActionEvent)


# --------------------------------------------------------------------------- #
# ------------------------------ User Commands ------------------------------ #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ---------- Helper function to validate the call of a user command ----------#
# --------------------------------------------------------------------------- #
async def isValidCall(ctx, commandInfo, args, extraArgs, adminOnly=False):

    # Usage string
    usage = f"Usage: `{prefix}{commandInfo['name']}"
    for command in commandInfo["args"]:
        usage += f" <{command}>"
    usage += "`"

    # # If we are not in a DM and need to be, stop here
    # if hasToBeDM and not isinstance(ctx.channel, discord.DMChannel):
    #     return False

    # If we aren't in one of the shop channels, stop here
    if ctx.channel.id not in DISCORD_SHOP_CHANNELS:
        return

    # If an admin did not send this message, return an error
    if adminOnly is True and ctx.author.id not in DISCORD_ADMINS:
        await send_embed(ctx, "Error",
                         "You do not have permission to use this command",
                         redHex)
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
# ------------------------------ Points Command ----------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='points')
async def points(ctx, user=None, *args):

    # If this isn't a valid call of this user command, stop here
    commandInfo = {"name": "points", "args": {}}
    isValid = await isValidCall(ctx, commandInfo, [], args)
    if not isValid:
        return

    # If one is given, search for the mentioned user
    # If the regular expression pattern can't find the user, return an error
    if user is None:
        userSearchResult = str(ctx.author.id)
    else:
        userSearchResult = userMentionPattern.search(user)
        if userSearchResult is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return
        userSearchResult = userSearchResult.group(1)

    # If we can't find the user given their ID, return an error
    user = bot.get_user(int(userSearchResult))
    if user is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # Return the number of points the user has
    userID = str(user.id)
    if userID not in points:
        userPoints = 0
    else:
        userPoints = points[userID]
    await send_embed(ctx, f"{user.name}\'s Points", f"{userPoints}",
                     greenHex)


# --------------------------------------------------------------------------- #
# ---------------------------- Purchase Command ----------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='purchase')
async def purchase(ctx, item=None, *args):

    # If this isn't a valid call of this user command, stop here
    commandInfo = {"name": "addproduct", "args": {"item": str}}
    isValid = await isValidCall(ctx, commandInfo, [item], args)
    if not isValid:
        return

    # If the item is not in the shop, return an error message
    if item not in shop:
        await send_embed(ctx, "Error", f"**{item}** is not in the shop.",
                         redHex)
        return

    # If the item is out of stock, return an error message
    if shop[item]["Stock"] <= 0:
        await send_embed(ctx, "Error", f"**{item}** is currenly out of stock.",
                         redHex)
        return

    # If the user doesn't have enough points, return an error message
    userID = str(ctx.author.id)
    if userID not in points:
        pointsNeeded = shop[item]["Points"]
    else:
        pointsNeeded = shop[item]["Points"] - points[userID]
    if pointsNeeded > 0:
        await send_embed(ctx, "Error",
                         f"You need {shop[item]['Points']} more points " +
                         "to purchase this item.", redHex)
        return

    # If we get to this point, make the purchase and return a success message
    if userID not in orders:
        orders[userID] = {}
    if item not in orders[userID]:
        orders[userID][item] = 1
    else:
        orders[userID][item] += 1

    points[userID] -= shop[item]["Points"]
    shop[item]["Stock"] -= 1

    saveData("orders", orders)
    saveData("points", points)
    saveData("shop", shop)

    await send_embed(ctx, "Success!",
                     f"You have purchased one {item}. " +
                     "Please open a ticket to claim it.", greenHex)


# --------------------------------------------------------------------------- #
# ------------------------------ Shop Command ------------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='shop')
# @commands.cooldown(1, 0.5, commands.BucketType.user)
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
# --------------------------------------------------------------------------- #
# ---------------------------- Add a new product  --------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='additem')
async def additem(ctx, productName=None, cost=None, stock=None, *args):

    # If this isn't a valid call of this admin command, stop here
    commandInfo = {"name": "additem",
                   "args": {"productName": str, "cost": int, "stock": int}}
    isValid = await isValidCall(ctx, commandInfo,
                                [productName, cost, stock], args,
                                adminOnly=True)
    if not isValid:
        return

    # Cast each argument to the proper type
    cost = int(cost)
    stock = int(stock)

    # If the product is already in the store, return an error
    if productName in shop:
        await send_embed(ctx, "Error",
                         f"**{productName}** is already in the shop",
                         redHex)
        return

    # Otherwise add it the shop and return a success message
    else:
        shop[productName] = {"Points": cost, "Stock": stock}
        saveData("shop", shop)
        await send_embed(ctx, "Success!",
                         f"**{productName}** has been added to the store " +
                         f"with a price of **{cost}** and " +
                         f"a stock of **{stock}**", greenHex)


# --------------------------------------------------------------------------- #
# ------------------- Add stock to an existing product  --------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='addstock')
async def addstock(ctx, productName=None, stock=None, *args):

    # If this isn't a valid call of this admin command, stop here
    commandInfo = {"name": "addstock",
                   "args": {"productName": str, "stock": int}}
    isValid = await isValidCall(ctx, commandInfo,
                                [productName, stock], args,
                                adminOnly=True)
    if not isValid:
        return

    # Cast each argument to the proper type
    stock = int(stock)

    # If the product is not in the shop, return an error
    if productName not in shop:
        await send_embed(ctx, "Error",
                         f"**{productName}** is not currently in the shop.",
                         redHex)
        return
    # Otherwise add the product's stock to the shop.
    else:
        shop[productName]["Stock"] = int(shop[productName]["Stock"]) + stock
    saveData("shop", shop)

    # Return a success message
    await send_embed(ctx, "Success!", f"**{productName}** now has a stock " +
                     f"of **{shop[productName]['Stock']}**", greenHex)


# --------------------------------------------------------------------------- #
# ----------------------------- Delete a product  --------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='deleteitem')
async def deleteitem(ctx, productName=None, *args):

    # If this isn't a valid call of this admin command, stop here
    commandInfo = {"name": "deleteitem",
                   "args": {"productName": str}}
    isValid = await isValidCall(ctx, commandInfo,
                                [productName], args,
                                adminOnly=True)
    if not isValid:
        return

    # If the product is not in the shop, return an error
    if productName not in shop:
        await send_embed(ctx, "Error",
                         f"**{productName}** is not currently in the shop.",
                         redHex)
        return

    # Otherwise delete it and return a success message
    del shop[productName]
    saveData("shop", shop)
    await send_embed(ctx, "Success!",
                     f"**{productName}** has been removed from the shop.",
                     greenHex)


# --------------------------------------------------------------------------- #
# ---------------------------- Fulfill an order  ---------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='fillorder')
async def fillorder(ctx, user=None, order=None, *args):

    # If this isn't a valid call of this admin command, stop here
    commandInfo = {"name": "fillorder",
                   "args": {"user": str, "order": str}}
    isValid = await isValidCall(ctx, commandInfo,
                                [user, order], args,
                                adminOnly=True)
    if not isValid:
        return

    # If the regular expression pattern can't find the user, return an error
    userSearchResult = userMentionPattern.search(user)
    if userSearchResult is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # If we can't find the user given their ID, return an error
    user = bot.get_user(int(userSearchResult.group(1)))
    if user is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # If the order does not exist, return an error
    userIDStr = str(user.id)
    if userIDStr not in orders or order not in orders[userIDStr]:
        await send_embed(ctx, "Error",
                         f'{user.name} does not have a pending ' +
                         'order for "{order}".', redHex)
        return

    # Remove the order and return a success message
    if orders[userIDStr][order] <= 1:
        del orders[userIDStr][order]
    else:
        orders[userIDStr][order] -= 1

    saveData("oders", orders)
    await send_embed(ctx, "Success!",
                     f"{user.name}\'s order of {order} has been fulilled",
                     greenHex)


# --------------------------------------------------------------------------- #
# -------------------------- Give a user points  ---------------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='givepoints')
async def givepoints(ctx, user=None, amount=None, *args):

    # If this isn't a valid call of this admin command, stop here
    commandInfo = {"name": "givepoints",
                   "args": {"user": str, "amount": int}}
    isValid = await isValidCall(ctx, commandInfo,
                                [user, amount], args,
                                adminOnly=True)
    if not isValid:
        return

    # Cast each argument to the proper type
    amount = int(amount)

    # If the regular expression pattern can't find the user, return an error
    userSearchResult = userMentionPattern.search(user)
    if userSearchResult is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # If we can't find the user given their ID, return an error
    user = bot.get_user(int(userSearchResult.group(1)))
    if user is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # If we get to this point, add the points to the user
    # and return a success message
    userIDStr = str(user.id)
    if userIDStr in points:
        points[userIDStr] += amount
    else:
        points[userIDStr] = amount
    await send_embed(ctx, "Success!",
                     f"{user.name} now has {points[userIDStr]} points.",
                     greenHex)
    saveData("points", points)


# --------------------------------------------------------------------------- #
# --------------------- Get a user's purchased orders  ---------------------- #
# --------------------------------------------------------------------------- #
@bot.command(name='orders')
async def orders(ctx, user=None, *args):

    # If this isn't a valid call of this admin command, stop here
    commandInfo = {"name": "orders",
                   "args": {"user": str}}
    isValid = await isValidCall(ctx, commandInfo,
                                [user], args,
                                adminOnly=True)
    if not isValid:
        return

    # If the regular expression pattern can't find the user, return an error
    userSearchResult = userMentionPattern.search(user)
    if userSearchResult is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # If we can't find the user given their ID, return an error
    user = bot.get_user(int(userSearchResult.group(1)))
    if user is None:
        await send_embed(ctx, "Error", "User not found.", redHex)
        return

    # Return the user's orders
    userIDStr = str(user.id)
    if userIDStr not in orders or len(orders[userIDStr]) == 0:
        await send_embed(ctx, f"{user.name}\'s Purchases",
                         f"{user.name} does not have any active orders",
                         greenHex)
        return
    else:
        description = ""
        for purchase in orders[userIDStr]:
            description += '\n'
            description += f"{purchase}: {orders[userIDStr][purchase]}"
        await send_embed(ctx, f"{user.name}\'s Purchases", description,
                         greenHex)

# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ------------------------------- Help Command ------------------------------ #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
userCommands = {}
userCommands["points"] = {
    "args":
    {
        "user (optional)":
            "Should be a mention (i.e. an `@`) of the user whose " +
            "points you'd like to see.",
    },
    "description":
        "Check how many points a user has. " +
        "Leave `<user>` blank to get your own point count.",
    "example":
        "!points @Permittivity"
}
userCommands["purchase"] = {
    "args":
    {
        "item":
            "The item which you'd like to purchase."
    },
    "description":
        "Used to purchase an item from the shop.",
    "example":
        '!purchase "Multi Word Product Name"'
}
userCommands["shop"] = {
    "args": {},
    "description":
        "View the items available to purchase.",
    "example":
        "!shop"
}

adminCommands = {}
adminCommands["additem"] = {
    "args":
    {
        "productName":
            "Name of the pdocut to add.",
        "cost":
            "Number of points this product costs.",
        "stock":
            "Stock of the product to add."
        },
    "description":
        "Add a new product to the shop.",
    "example":
        '!additem "Multi Word Product Name" 1000 1'
    }
adminCommands["addstock"] = {
    "args":
    {
        "productName":
            "Name of the product whose stock you want to change.",
        "stock":
            "Amount of stock to add (can be negative to reduce stock)."
    },
    "description":
        "Add stock to an existing item in the shop.",
    "example":
        '!addstock "Multi Word Product Name" 10'
}
adminCommands["deleteitem"] = {
    "args":
    {
        "productName":
            "Name of the product which you'd like to delete."
    },
    "description":
        "Remove an item from the shop.",
    "example":
        '!deleteitem "Multi Word Product Name"'
}
adminCommands["fillorder"] = {
    "args":
    {
        "user":
            "Should be a mention (i.e. an `@`) of the user whose " +
            "order you'd like to fulfill.",
        "order":
            "The name of the product which the user bought. " +
            "You can use `!orders <user>` to check their active orders."
    },
    "description":
        "Used to delete orders from a user's list of purchases.",
    "example":
        '!fillorder @Permittivity "Multi Word Product Name"'
}
adminCommands["givepoints"] = {
    "args":
    {
        "user":
            "Should be a mention (i.e. an `@`) of the user whom " +
            "you'd like to give points.",
        "amount":
            "The amount of points you'd like to add. " +
            "If you'd like to remove points, use a negative number."
    },
    "description":
        "Add `<amount>` points to `<user>`'s current point count.",
    "example":
        "!givepoints @Permittivity 100"
}
adminCommands["orders"] = {
    "args":
    {
        "user":
            "Should be a mention (i.e. an `@`) of the user whose " +
            "pending orders you'd like to see.",
    },
    "description":
        "Returns a user's pending orders.",
    "example":
        "!orders @Permittivity"
}


# Function to generate the description for a single command
def generateDescription(command, commandList, example=False):
    description = f"**Description:** {commandList[command]['description']}"
    description += '\n'
    description += f"**Usage:** `!{command}"
    for arg in commandList[command]["args"]:
        description += f" <{arg}>"
    description += '`'
    if example:
        description += '\n'
        description += f"**Example:** `{commandList[command]['example']}`"
    return description


@bot.command(name='help')
async def help(ctx, command=None, *args):

    # First deal with a specific command
    if command is not None:

        # If the command does not exist, return an error message
        doesNotExist = False
        if command in adminCommands:
            adminCommand = True
        else:
            adminCommand = False
        if command not in userCommands:
            doesNotExist = True
            adminCommand = False
            if ctx.author.id in DISCORD_ADMINS and command in adminCommands:
                doesNotExist = False
                adminCommand = True
        if doesNotExist:
            await send_embed(ctx, "Error", f"The command `!{command}` either" +
                             " does not exist or you don't have permission " +
                             "to use it.",
                             redHex)
            return

        # Display the help message for this command
        if adminCommand:
            description = generateDescription(command, adminCommands,
                                              example=True)
        else:
            description = generateDescription(command, userCommands,
                                              example=True)
        await send_embed(ctx, f"Help for !{command}", description, greenHex)

    # Now deal with the general help menu
    else:
        # First get the commands available to this user
        commands = list(userCommands.keys())
        if ctx.author.id in DISCORD_ADMINS:
            commands += list(adminCommands.keys())
        commands.sort()

        description = "To get more information about a particular, "
        description += "command, try `!help <command>`\n\n"
        for command in commands:
            description += f"`!{command}`"
            if command in adminCommands:
                description += f" (Admin Only)\n"
                description += generateDescription(command, adminCommands)
            else:
                description += '\n'
                description += generateDescription(command, userCommands)
            description += '\n\n'

        await send_embed(ctx, "**Available Commands**", description,
                         greenHex)


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# -------------------------------- Enter Here ------------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":

    # Get the group name
    groupName = input("What is the group name?\n")

    # Load group settings
    with open(f"./{groupName}/info.json", "r") as f:
        info = json.load(f)
        f.close()
    DISCORD_BOT_ID = int(info["DISCORD_BOT_ID"])
    DISCORD_SUCCESS_CHANNEL_ID = int(info["DISCORD_SUCCESS_CHANNEL_ID"])
    DISCORD_SHOP_CHANNELS = []
    for channelID in info["DISCORD_SHOP_CHANNELS"]:
        DISCORD_SHOP_CHANNELS.append(int(channelID))
    DISCORD_ADMINS = []
    for adminID in info["DISCORD_ADMINS"]:
        DISCORD_ADMINS.append(int(adminID))

    # Load the saved data
    points = loadData("points")
    orders = loadData("orders")
    shop = loadData("shop")

    # Load twitter stuff
    twitterStuffString = open(f"./{groupName}/twitterStuff.txt").read()
    twitterStuff = json.loads(twitterStuffString)

    # Start the bot
    discordToken = open(f"./{groupName}/discordToken.txt").read()
    bot.run(discordToken)
