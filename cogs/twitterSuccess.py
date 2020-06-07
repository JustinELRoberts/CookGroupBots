import discord
import twitter
import json
import re

# ID of the discord bot
# (can be found by posting something with the bot and checking ctx.author.id)
DISCORD_BOT_ID = 650713254322241559

# ID of the Discord channel whose messages you want to post to twitter
# (can be found by posting something in this channel
# and checking ctx.channel.id)
DISCORD_CHANNEL_ID = 710479705798869143

# Color used for embeds
discordHex = 0xfbde67
successHex = 0x00ff00
failureHex = 0xff0000

# The prefix used in bot commands (e.g. !help)
prefix = '!'

# Regex matching patterns
hyperlink_url_pattern = re.compile(r"\((.+)\)")
tweet_id_pattern = re.compile(r"/status/(\d+)")

# Load the discord api
client = discord.Client()


# ----------------------------- Discord Funcs ------------------------------- #
# Function to send a basic embed
async def send_embed(ctx, title, description, color, fields=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields is not None:
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"])
    await ctx.send(embed=embed)


# Get the linked jump url from the embed's added field
def get_linked_jump_url(embed):
    for field in embed.fields:
        if field.name == "Your Post":
            jump_url = hyperlink_url_pattern.search(field.value).group(1)
            return jump_url
    return None


# ----------------------------- Twitter Funcs ------------------------------- #
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


# ---------------------------- on_message Event ----------------------------- #
mediaExt = ['.jpg', '.png', '.jpeg', '.mp4']
@client.event
async def on_message(message):

    # If the bot sent this message, stop here
    if message.author.id == DISCORD_BOT_ID:
        return

    # If this is not sent from the proper channel, stop here
    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    # Otherwise iterate through all the images sent and post them to twitter
    msgLink = message.jump_url
    isAttached = False
    fields = []
    for attachment in message.attachments:
        isAttached = True
        tweetURL = post_tweet(attachment.url, message.author)
        fields.append({"name": "Your Post", "value": f"[Here]({msgLink})"})
        fields.append({"name": "Tweet", "value": f"[Here]({tweetURL})"})

    # If the message sent was an image link, post it to twitter
    for ext in mediaExt:
        if message.content.endswith(ext):
            isAttached = True
            tweetURL = post_tweet(message. content, message.author)
            fields.append({"name": "Your Post", "value": f"[Here]({msgLink})"})
            fields.append({"name": "Tweet", "value": f"[Here]({tweetURL})"})

    if isAttached:
        await send_embed(message.channel, "Success!",
                         "Your success has been post to Twitter.\n" +
                         "Please react with ❌ if you'd like to " +
                         "remove the post", successHex, fields)
        await message.add_reaction('❌')
    else:
        await send_embed(message.channel, "Error", "Please make sure you " +
                         "include an image or video in your post.", failureHex)


# -------------------------  on_reaction_add Event -------------------------- #
@client.event
async def on_raw_reaction_add(rawReactionActionEvent):

    # Get the channel and message this react occured in
    user = client.get_user(rawReactionActionEvent.user_id)
    channel = client.get_channel(rawReactionActionEvent.channel_id)
    message = await channel.fetch_message(rawReactionActionEvent.message_id)

    # If this is not sent from the proper channel, stop here
    if channel.id != DISCORD_CHANNEL_ID:
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


# -------------------------------- Enter Here ------------------------------- #
# Start the bot
if __name__ == "__main__":
    # Load twitter stuff
    twitterStuffString = open("./twitterStuff.txt").read()
    twitterStuff = json.loads(twitterStuffString)

    # Start the bot
    discordToken = open("./discordToken.txt").read()
    client.run(discordToken)
