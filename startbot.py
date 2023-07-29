import discord
from discord.ext import commands

if __name__ == "__main__":
    client = commands.Bot(command_prefix='$', case_insensitive=True, help_command=None)
    # open and obtain token id for the discord bot
    with open("env.txt", 'r') as file:
        for line in file:
            if "botkey" in line:
                client.token_id = line[line.find(":")+1::]
            elif "youtubeapikey" in line:
                client.youtube_api_key = line[line.find(":")+1::]

    # loads other commands from seperate files
    extensions = ["helplog", "musicplayer"]
    for ext in extensions:
            client.load_extension(ext)

@client.event
async def on_ready():
    #notify the user the bot is online
    print("Discord version: ", discord.__version__, "\n{0.user} has arrived!".format(client))
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="POP POP POP"))
    general_channel = client.get_channel(954548409396785162)
    await general_channel.send(f"{client.user.name} is in the house!")
    await general_channel.send("https://c.tenor.com/6zDvbZxfgTsAAAAM/hippie-dj.gif")

client.run(client.token_id)

