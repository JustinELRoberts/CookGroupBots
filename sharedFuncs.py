import discord


# Function to send a basic embed
async def send_embed(ctx, title, desc, color, fields=None):
    embed = discord.Embed(title=title, description=desc, color=color)
    if fields is not None:
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"],
                            inline=field["inline"])
    return await ctx.send(embed=embed)