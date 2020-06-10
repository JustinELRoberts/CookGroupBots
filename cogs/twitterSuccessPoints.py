from sharedFuncs import send_embed
from discord.ext import commands
import discord
import twitter
import json
import math
import re
import os

# UI settings
successPoints = 10
itemsPerPage = 5

# Colors used for embeds
greenHex = 0x00ff00
yellowHex = 0xfbde67
redHex = 0xff0000
shopHex = 0x00ff00

# Regex matching patterns
hyperlinkUrlPattern = re.compile(r"\((.+)\)")
tweetIdPattern = re.compile(r"/status/(\d+)")
userMentionPattern = re.compile(r"<@!(\d+)>")

# Used for adding reactions for shop page navigation
numberEmojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣',
                '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

# Extensions for media to post to twitter
mediaExt = ['.jpg', '.png', '.jpeg', '.mp4']


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ------------------------ TwitterSuccessPoints Cog ------------------------- #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
class twitterSuccessPoints(commands.Cog):

    # ----------------------------------------------------------------------- #
    # ---------------------------- Initialization --------------------------- #
    # ----------------------------------------------------------------------- #
    def __init__(self, bot):
        self.bot = bot

        # Add the information for this cog's `!help` command
        self.addHelpInfo()

        # Load the saved data
        self.points = self.loadData("points")
        self.orders = self.loadData("orders")
        self.shop = self.loadData("shop")

        # Load group settings
        self.bot.info['groupName'] = self.bot.info['groupName']
        relPath = f"../groups/{self.bot.info['groupName']}/info.json"
        myPath = os.path.abspath(os.path.dirname(__file__))
        absPath = os.path.join(myPath, relPath)
        with open(absPath, "r") as f:
            info = json.load(f)
            f.close()
        self.id = int(info["botID"])
        self.successChannel = info["twitterSuccessPoints"]["successChannel"]
        self.successChannel = int(self.successChannel)
        self.allowedChannels = []
        for channel in info["twitterSuccessPoints"]["channels"]:
            self.allowedChannels.append(int(channel))

    # ----------------------------------------------------------------------- #
    # ---------------------------- Helper Funcs ----------------------------- #
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    # --------------------------- Discord Funcs ----------------------------- #
    # ----------------------------------------------------------------------- #
    # Generate and return the fields for a certain page for the shop
    def generatePageFields(self, page):
        fields = []
        indices = [(page - 1) * itemsPerPage, page * itemsPerPage]
        items = list(self.shop.items())[indices[0]:indices[1]]
        for item in sorted(items, key=lambda item: item[1]["Points"]):
            name = item[0]
            points = item[1]["Points"]
            stock = item[1]["Stock"]
            fields.append({"name": f"**{name}**",
                           "value": f"Cost: {points} points\nStock: {stock}",
                           "inline": False})
        return fields

    # ----------------------------------------------------------------------- #
    # --------------------------- Twitter Funcs ----------------------------- #
    # ----------------------------------------------------------------------- #
    # Get the linked tweet url from the embed's added field
    def get_tweet_url(self, embed):
        for field in embed.fields:
            if field.name == "Tweet":
                tweet_url = hyperlinkUrlPattern.search(field.value).group(1)
                return tweet_url
        return None

    # Post an image to twitter from a link
    def post_tweet(self, url, discordName):

        # Login to twitter
        twitterStuff = self.bot.info["twitter"]
        api = twitter.Api(consumer_key=twitterStuff["key"],
                          consumer_secret=twitterStuff["secret"],
                          access_token_key=twitterStuff["token"],
                          access_token_secret=twitterStuff["tokenSecret"],
                          sleep_on_rate_limit=True)

        # Tweet the image/video
        statusObj = api.PostUpdate(status=f"Success from {discordName}",
                                   media=url)

        return statusObj.media[0].expanded_url

    # Delete a tweet, given its url
    def delete_tweet(self, tweet_url):

        # Login to twitter
        twitterStuff = self.bot.info["twitter"]
        api = twitter.Api(consumer_key=twitterStuff["key"],
                          consumer_secret=twitterStuff["secret"],
                          access_token_key=twitterStuff["token"],
                          access_token_secret=twitterStuff["tokenSecret"],
                          sleep_on_rate_limit=True)

        # Get the tweet's id
        tweetID = tweetIdPattern.search(tweet_url).group(1)

        # Delete the post
        api.DestroyStatus(tweetID)

    # ----------------------------------------------------------------------- #
    # ----------------------- Data Management Funcs ------------------------- #
    # ----------------------------------------------------------------------- #
    # ---------------------- General Data Management ------------------------ #
    # Function to load the current point dict
    def loadData(self, dataType):

        # Return an empty dict if we havent stored anything yet
        groupName = self.bot.info['groupName']
        relPath = f"../groups/{groupName}/shop/{dataType}.json"
        myPath = os.path.abspath(os.path.dirname(__file__))
        absPath = os.path.join(myPath, relPath)
        if not os.path.exists(absPath):
            return {}

        # If we have, load it and return the result
        with open(absPath, 'r') as f:
            loadedData = json.load(f)
            f.close()
        return loadedData

    # Function to save the current point dict
    def saveData(self, dataType, data):
        groupName = self.bot.info['groupName']
        relPath = f"../groups/{groupName}/shop/{dataType}.json"
        myPath = os.path.abspath(os.path.dirname(__file__))
        absPath = os.path.join(myPath, relPath)
        with open(absPath, 'w+') as f:
            json.dump(data, f)
            f.close

    # ----------------------------------------------------------------------- #
    # ------------------------- Point Management ---------------------------- #
    # ----------------------------------------------------------------------- #
    # Function to add points to the user who's discordID is `id`
    # By default, adds `successPoints` points
    def addPoints(self, id, amount=successPoints):
        id = str(id)
        if id not in self.points.keys():
            self.points[id] = amount
        else:
            self.points[id] += amount
        self.saveData("points", self.points)

    # Funtion which returns the number of points for a given user
    def getPoints(self, id):
        id = str(id)
        return self.points[id]

    # ----------------------------------------------------------------------- #
    # ------------------------------- Events -------------------------------- #
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    # -------------------------- on_message Event --------------------------- #
    # ----------------------------------------------------------------------- #
    # Get the linked jump url from the embed's added field
    def get_linked_jump_url(self, embed):
        for field in embed.fields:
            if field.name == "Your Post":
                jumpURL = hyperlinkUrlPattern.search(field.value).group(1)
                return jumpURL
        return None

    # Function to respond to success posts
    async def respondToSuccess(self, message):

        # Otherwise iterate through all the images sent and post them to twit
        msgLink = message.jump_url
        isAttached = False
        fields = []
        for attachment in message.attachments:
            isAttached = True
            tweetURL = self.post_tweet(attachment.url, message.author)
            self.addPoints(message.author.id)
            fields.append({"name": "Your Post", "value": f"[Here]({msgLink})",
                           "inline": True})
            fields.append({"name": "Tweet", "value": f"[Here]({tweetURL})",
                           "inline": True})

        # If the message sent was an image link, post it to twitter
        for ext in mediaExt:
            if message.content.endswith(ext):
                isAttached = True
                tweetURL = self.post_tweet(message. content, message.author)
                self.addPoints(message.author.id)
                fields.append({"name": "Your Post",
                               "value": f"[Here]({msgLink})",
                               "inline": True})
                fields.append({"name": "Tweet",
                               "value": f"[Here]({tweetURL})",
                               "inline": True})

        if isAttached:
            currPoints = self.getPoints(message.author.id)
            await send_embed(message.channel, "Success!",
                             "Your success has been post to Twitter. " +
                             f"You have {currPoints} points.\n " +
                             "Please react with ❌ if you'd " +
                             "like to remove the post", greenHex, fields)
            await message.add_reaction('❌')
        else:
            await send_embed(message.channel, "Error",
                             "Please make sure you " +
                             "include an image or video in your post.",
                             redHex)

    @commands.Cog.listener()
    async def on_message(self, message):

        # If the bot sent this message, stop here
        if message.author.id == self.id:
            return

        # If this sent from success, repond to it
        if message.channel.id == self.successChannel:
            await self.respondToSuccess(message)

        # Otherwise process commands
        # await self.bot.process_commands(message)

    # ----------------------------------------------------------------------- #
    # -----------------------  on_reaction_add Event ------------------------ #
    # ----------------------------------------------------------------------- #
    # Helper function to unpack a rawReactionActionEvent
    # Returns a dict containing useful information about the reaction
    async def unpackRawReactActEvent(self, reactionEvent):
        authorID = reactionEvent.user_id
        user = self.bot.get_user(authorID)
        channel = self.bot.get_channel(reactionEvent.channel_id)
        message = await channel.fetch_message(reactionEvent.message_id)
        return (authorID, user, channel, message)

    # Function used to add functionality for post deletion when reacting
    # to a post
    async def deleteSuccess(self, authorID, user, channel, message, event):

        # If this is not sent from the proper channel, stop here
        if channel.id != self.successChannel:
            return

        # If the reaction was sent by us, stop here
        if user.id == self.id:
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
            if len(post.embeds) == 0:
                continue
            jump_url = self.get_linked_jump_url(post.embeds[0])
            # Once we find the message, delete the tweet,
            # user post, and bot post
            if jump_url == message.jump_url:
                tweet_url = self.get_tweet_url(post.embeds[0])
                self.delete_tweet(tweet_url)
                await post.delete()
                await message.delete()
                self.addPoints(authorID, -successPoints)
                await send_embed(message.channel, f"{message.author}",
                                 "Your success has been deleted " +
                                 "from Twitter.\nYou have " +
                                 f"{self.getPoints(authorID)} points.\n",
                                 redHex)

    # Function to edit a shop post to change pages
    async def shopNavigation(self, authorID, user, channel, message, event):

        # Get additional info
        author = self.bot.get_user(authorID)
        emoji = event.emoji

        # If this is not sent from the proper channel, stop here
        if channel.id not in self.allowedChannels:
            return

        # If the reaction was sent by us, stop here
        if user.id == self.id:
            return

        # If the message itself is not one of the shop messages, stop here
        if len(message.embeds) != 1:
            return
        embed = message.embeds[0]
        groupName = self.bot.info['groupName']
        if f"**{groupName} Shop Page" not in embed.description:
            return

        # If the reaction isnt a number emoji, remove it and stop here
        if emoji.name not in numberEmojis:
            await message.remove_reaction(emoji, author)
            return

        # If we get to this point, we need change shop pages
        pageNum = numberEmojis.index(emoji.name) + 1
        fields = self.generatePageFields(page=pageNum)
        desc = f"🎁 **{self.bot.info['groupName']} Shop Page 1** 🎁"
        embed = discord.Embed(title="",
                              description=desc,
                              color=shopHex)
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"],
                            inline=field["inline"])
        await message.edit(embed=embed)

        # Remove the reaction
        await message.remove_reaction(emoji, author)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, rawReactionActionEvent):
        e = rawReactionActionEvent
        authorID, user, channel, message = await self.unpackRawReactActEvent(e)
        await self.deleteSuccess(authorID, user, channel, message,
                                 rawReactionActionEvent)
        await self.shopNavigation(authorID, user, channel, message,
                                  rawReactionActionEvent)

    # ----------------------------------------------------------------------- #
    # ---------------------------- User Commands ---------------------------- #
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    # ---------- Helper function to validate the call of a command ---------- #
    # ----------------------------------------------------------------------- #
    async def isValidCall(self, ctx, commandInfo, args, extraArgs,
                          adminOnly=False):

        # Usage string
        usage = f"Usage: `{self.bot.command_prefix}{commandInfo['name']}"
        for command in commandInfo["args"]:
            usage += f" <{command}>"
        usage += "`"

        # # If we are not in a DM and need to be, stop here
        # if hasToBeDM and not isinstance(ctx.channel, discord.DMChannel):
        #     return False

        # If we aren't in one of the shop channels, stop here
        if ctx.channel.id not in self.allowedChannels:
            return

        # If an admin did not send this message, return an error
        if adminOnly is True and ctx.author.id not in self.bot.info["admins"]:
            await send_embed(ctx, "Error",
                             "You do not have permission " +
                             "to use this command",
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

    # ----------------------------------------------------------------------- #
    # ---------------------------- Points Command --------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='points')
    async def pointsCommand(self, ctx, user=None, *args):

        # If this isn't a valid call of this user command, stop here
        commandInfo = {"name": "points", "args": {}}
        isValid = await self.isValidCall(ctx, commandInfo, [], args)
        if not isValid:
            return

        # If one is given, search for the mentioned user
        # If the regular expression pattern can't find the user,
        # return an error
        if user is None:
            userSearchResult = str(ctx.author.id)
        else:
            userSearchResult = userMentionPattern.search(user)
            if userSearchResult is None:
                await send_embed(ctx, "Error", "User not found.", redHex)
                return
            userSearchResult = userSearchResult.group(1)

        # If we can't find the user given their ID, return an error
        user = self.bot.get_user(int(userSearchResult))
        if user is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # Return the number of points the user has
        userID = str(user.id)
        if userID not in self.points:
            userPoints = 0
        else:
            userPoints = self.points[userID]
        await send_embed(ctx, f"{user.name}\'s Points", f"{userPoints}",
                         greenHex)

    # ----------------------------------------------------------------------- #
    # -------------------------- Purchase Command --------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='purchase')
    async def purchase(self, ctx, item=None, *args):

        # If this isn't a valid call of this user command, stop here
        commandInfo = {"name": "addproduct", "args": {"item": str}}
        isValid = await self.isValidCall(ctx, commandInfo, [item], args)
        if not isValid:
            return

        # If the item is not in the shop, return an error message
        if item not in self.shop:
            await send_embed(ctx, "Error",
                             f"**{item}** is not in the shop.",
                             redHex)
            return

        # If the item is out of stock, return an error message
        if self.shop[item]["Stock"] <= 0:
            await send_embed(ctx, "Error",
                             f"**{item}** is currenly out of stock.",
                             redHex)
            return

        # If the user doesn't have enough points, return an error message
        userID = str(ctx.author.id)
        if userID not in self.points:
            pointsNeeded = self.shop[item]["Points"]
        else:
            pointsNeeded = self.shop[item]["Points"] - self.points[userID]
        if pointsNeeded > 0:
            neededPoints = self.shop[item]['Points']
            await send_embed(ctx, "Error",
                             f"You need {neededPoints} more points " +
                             "to purchase this item.", redHex)
            return

        # If we get to this point, make the purchase and return a
        # success message
        if userID not in self.orders:
            self.orders[userID] = {}
        if item not in self.orders[userID]:
            self.orders[userID][item] = 1
        else:
            self.orders[userID][item] += 1

        self.points[userID] -= self.shop[item]["Points"]
        self.shop[item]["Stock"] -= 1

        self.saveData("orders", self.orders)
        self.saveData("points", self.points)
        self.saveData("shop", self.shop)

        await send_embed(ctx, "Success!",
                         f"You have purchased one {item}. " +
                         "Please open a ticket to claim it.", greenHex)

    # ----------------------------------------------------------------------- #
    # ---------------------------- Shop Command ----------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='shop')
    async def shopCommand(self, ctx):

        # If this isn't one of the channels where we take commands, stop here
        if ctx.channel.id not in self.allowedChannels:
            return

        # If the shop is empty, alert the user
        if len(self.shop) == 0:
            await send_embed(ctx, "__Shop Page 1__",
                                  "The shop is empty 😔",
                                  shopHex)
            return

        # Otherwise display the shop's first page,
        # containing `itemsPerPage` items
        fields = self.generatePageFields(page=1)
        desc = f"🎁 **{self.bot.info['groupName']} Shop Page 1** 🎁"
        message = await send_embed(ctx, "", desc, shopHex, fields)

        # Add reactions for page navigation
        numPages = math.ceil(len(self.shop.keys()) / itemsPerPage)
        for num in range(numPages):
            await message.add_reaction(numberEmojis[num])

    # ----------------------------------------------------------------------- #
    # ---------------------------- Admin Commands --------------------------- #
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    # -------------------------- Add a new product  ------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='additem')
    async def additem(self, ctx, productName=None, cost=None, stock=None,
                      *args):

        # If this isn't a valid call of this admin command, stop here
        commandInfo = {"name": "additem",
                       "args": {"productName": str, "cost": int, "stock": int}}
        isValid = await self.isValidCall(ctx, commandInfo,
                                         [productName, cost, stock], args,
                                         adminOnly=True)
        if not isValid:
            return

        # Cast each argument to the proper type
        cost = int(cost)
        stock = int(stock)

        # If the product is already in the store, return an error
        if productName in self.shop:
            await send_embed(ctx, "Error",
                             f"**{productName}** is already in the shop",
                             redHex)
            return

        # Otherwise add it the shop and return a success message
        else:
            self.shop[productName] = {"Points": cost, "Stock": stock}
            self.saveData("shop", self.shop)
            await send_embed(ctx, "Success!",
                             f"**{productName}** has been added to " +
                             f"the store with a price of **{cost}** " +
                             f"and a stock of **{stock}**", greenHex)

    # ----------------------------------------------------------------------- #
    # ----------------- Add stock to an existing product  ------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='addstock')
    async def addstock(self, ctx, productName=None, stock=None, *args):

        # If this isn't a valid call of this admin command, stop here
        commandInfo = {"name": "addstock",
                       "args": {"productName": str, "stock": int}}
        isValid = await self.isValidCall(ctx, commandInfo,
                                         [productName, stock], args,
                                         adminOnly=True)
        if not isValid:
            return

        # Cast each argument to the proper type
        stock = int(stock)

        # If the product is not in the shop, return an error
        if productName not in self.shop:
            await send_embed(ctx, "Error",
                             f"**{productName}** is not currently " +
                             "in the shop.", redHex)
            return
        # Otherwise add the product's stock to the shop.
        else:
            currStock = int(self.shop[productName]["Stock"])
            self.shop[productName]["Stock"] = currStock + stock
        self.saveData("shop", self.shop)

        # Return a success message
        await send_embed(ctx, "Success!",
                         f"**{productName}** now has a stock " +
                         f"of **{self.shop[productName]['Stock']}**",
                         greenHex)

    # ----------------------------------------------------------------------- #
    # --------------------------- Delete a product  ------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='deleteitem')
    async def deleteitem(self, ctx, productName=None, *args):

        # If this isn't a valid call of this admin command, stop here
        commandInfo = {"name": "deleteitem",
                       "args": {"productName": str}}
        isValid = await self.isValidCall(ctx, commandInfo,
                                         [productName], args,
                                         adminOnly=True)
        if not isValid:
            return

        # If the product is not in the shop, return an error
        if productName not in self.shop:
            await send_embed(ctx, "Error",
                             f"**{productName}** isn't currently " +
                             "in the shop.", redHex)
            return

        # Otherwise delete it and return a success message
        del self.shop[productName]
        self.saveData("shop", self.shop)
        await send_embed(ctx, "Success!",
                         f"**{productName}** has been " +
                         "removed from the shop.", greenHex)

    # ----------------------------------------------------------------------- #
    # -------------------------- Fulfill an order  -------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='fillorder')
    async def fillorder(self, ctx, user=None, order=None, *args):

        # If this isn't a valid call of this admin command, stop here
        commandInfo = {"name": "fillorder",
                       "args": {"user": str, "order": str}}
        isValid = await self.isValidCall(ctx, commandInfo,
                                         [user, order], args,
                                         adminOnly=True)
        if not isValid:
            return

        # If the regular expression pattern can't find the user,
        # return an error
        userSearchResult = userMentionPattern.search(user)
        if userSearchResult is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # If we can't find the user given their ID, return an error
        user = self.bot.get_user(int(userSearchResult.group(1)))
        if user is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # If the order does not exist, return an error
        userIDStr = str(user.id)
        if userIDStr not in self.orders or order not in self.orders[userIDStr]:
            await send_embed(ctx, "Error",
                             f'{user.name} does not have a pending ' +
                             'order for "{order}".', redHex)
            return

        # Remove the order and return a success message
        if self.orders[userIDStr][order] <= 1:
            del self.orders[userIDStr][order]
        else:
            self.orders[userIDStr][order] -= 1

        self.saveData("oders", self.orders)
        await send_embed(ctx, "Success!",
                         f"{user.name}\'s order of " +
                         f"{order} has been fulilled", greenHex)

    # ----------------------------------------------------------------------- #
    # ------------------------ Give a user points  -------------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='givepoints')
    async def givepoints(self, ctx, user=None, amount=None, *args):

        # If this isn't a valid call of this admin command, stop here
        commandInfo = {"name": "givepoints",
                       "args": {"user": str, "amount": int}}
        isValid = await self.isValidCall(ctx, commandInfo,
                                         [user, amount], args,
                                         adminOnly=True)
        if not isValid:
            return

        # Cast each argument to the proper type
        amount = int(amount)

        # If the regular expression pattern can't find the user,
        # return an error
        userSearchResult = userMentionPattern.search(user)
        if userSearchResult is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # If we can't find the user given their ID, return an error
        user = self.bot.get_user(int(userSearchResult.group(1)))
        if user is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # If we get to this point, add the points to the user
        # and return a success message
        userIDStr = str(user.id)
        if userIDStr in self.points:
            self.points[userIDStr] += amount
        else:
            self.points[userIDStr] = amount
        await send_embed(ctx, "Success!",
                         f"{user.name} now has " +
                         f"{self.points[userIDStr]} points.", greenHex)
        self.saveData("points", self.points)

    # ----------------------------------------------------------------------- #
    # ------------------- Get a user's purchased orders  -------------------- #
    # ----------------------------------------------------------------------- #
    @commands.command(name='orders')
    async def ordersCommand(self, ctx, user=None, *args):

        # If this isn't a valid call of this admin command, stop here
        commandInfo = {"name": "orders",
                       "args": {"user": str}}
        isValid = await self.isValidCall(ctx, commandInfo,
                                         [user], args,
                                         adminOnly=True)
        if not isValid:
            return

        # If the regular expression pattern can't find the user,
        # return an error
        userSearchResult = userMentionPattern.search(user)
        if userSearchResult is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # If we can't find the user given their ID, return an error
        user = self.bot.get_user(int(userSearchResult.group(1)))
        if user is None:
            await send_embed(ctx, "Error", "User not found.", redHex)
            return

        # Return the user's orders
        userIDStr = str(user.id)
        if userIDStr not in self.orders or len(self.orders[userIDStr]) == 0:
            await send_embed(ctx, f"{user.name}\'s Purchases",
                             f"{user.name} does not have any " +
                             "active orders", greenHex)
            return
        else:
            description = ""
            for order in self.orders[userIDStr]:
                description += '\n'
                description += f"{order}: {self.orders[userIDStr][order]}"
            await send_embed(ctx, f"{user.name}\'s Purchases",
                             description, greenHex)

    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    # ------------------------------ Help Stuff ----------------------------- #
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    def addHelpInfo(self):
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
                    "Name of the product to add.",
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
                    "You can use `!orders <user>` to check active orders."
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
        self.bot.helpInfo["twitterSuccessPoints"] = {}
        self.bot.helpInfo["twitterSuccessPoints"]["user"] = userCommands
        self.bot.helpInfo["twitterSuccessPoints"]["admin"] = adminCommands


# --------------------------------------------------------------------------- #
# ----------------------------- Initialize Cog ------------------------------ #
# --------------------------------------------------------------------------- #
def setup(bot):
    bot.add_cog(twitterSuccessPoints(bot))
