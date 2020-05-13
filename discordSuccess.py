import discord
import twitter
import json

# ID of the discord bot 
# (can be found by posting something with the bot and checking ctx.author.id)
DISCORD_BOT_ID = 0

# ID of the Discord channel whose messages you want to post to twitter
# (can be found by posting something in this channel and checking ctx.channel.id)
DISCORD_CHANNEL_ID = 0

# Color used for embeds
yellowHex = 0xfbde67

# The prefix used in bot commands (e.g. !help)
prefix = '!'

# Load the discord api
client = discord.Client()


# --------------------------------- Funcs ------------------------------------ #
# Function to send a basic embed
async def send_embed(ctx, title, description, color):
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)


# Function to post an image to twitter from a link
def post(url, discordName):

    # Login to twitter
    api = twitter.Api(consumer_key=twitterStuff["key"],
                      consumer_secret=twitterStuff["secret"],
                      access_token_key=twitterStuff["token"],
                      access_token_secret=twitterStuff["tokenSecret"],
                      sleep_on_rate_limit=True)


    # Tweet the image/video
    api.PostUpdate(status=f"Success from {discordName}", media=url)


# ---------------------------- on_message Event ------------------------------ #
mediaExt = ['.jpg', '.png', '.jpeg', '.mp4']
@client.event
async def on_message(ctx):

    # If the bot sent this message, stop here
    if ctx.author.id == DISCORD_BOT_ID:
        return

    # If this is not sent from the proper channel, stop here
    if ctx.channel.id != DISCORD_CHANNEL_ID:
        return

    # Otherwise iterate through all the images sent and post them to twitter
    for attachment in ctx.attachments:
        post(attachment.url, ctx.author)

    # If the message sent was an image link, post it to twitter
    for ext in mediaExt:
        if ctx.content.endswith(ext):
            post(ctx.content, ctx.author)

    await send_embed(ctx.channel, "", "Success posted to Twitter", yellowHex)


# -------------------------------- Enter Here -------------------------------- #
# Start the bot
if __name__ == "__main__":
    # Load twitter stuff
    twitterStuffString = open("./twitterStuff.txt").read()
    twitterStuff = json.loads(twitterStuffString)

    # Start the bot
    discordToken = open("./discordToken.txt").read()
    client.run(discordToken)