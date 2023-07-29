from discord.ext import commands
import discord

class help_log(commands.Cog):
    def __init__(self , bot):
        self.bot = bot

    #creates an embed with all the commands shown and their channel access
    @discord.slash_command()
    async def help(self,ctx):
        embed_color = discord.Color.gold()
        embed_musicplayer_command = discord.Embed(title="Music Player", color=embed_color)
        embed_musicplayer_command.set_thumbnail(url="https://media.tenor.com/LYUe1FNHN-UAAAAC/cat-headphones.gif")
        embed_musicplayer_command.add_field(name="Slash Commands", value="Accepts Songs/Playlists,  must be in voice channel in order to use commands, use the prefix / for the commands below:",inline=False)
        embed_musicplayer_command.add_field(name="dc", value="Disconnects and resets the bots state\n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="shutdown", value="Disconnects and resets the bots state and shuts down the p program \n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="clear", value="Clears/resets bots data and stops music player \n(channel: ALL)", inline=False)
        embed_musicplayer_command.add_field(name="queue (link here)", value="Queues up song/playlist/mix playlist \n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="searchsong (songtitle and artist(optional) here)", value="Queues up song searching from youtube for a lyrics video\n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="goto (index here)", value="Play the song at specific index \n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="skip", value="plays next song \n(channel: ALL)", inline=False)
        embed_musicplayer_command.add_field(name="previous", value="Plays the previous song \n(channel: ALL)", inline=False)
        embed_musicplayer_command.add_field(name="loop", value="Loops current song playing \n(channel: ALL)", inline=False)
        embed_musicplayer_command.add_field(name="resume",value="Resumes the current song\n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="pause", value="Pauses the current song \n(channel: ALL)", inline=False)
        embed_musicplayer_command.add_field(name="current",value="sends a message to the channel of the current song playing \n(channel: ALL)",inline=False)
        embed_musicplayer_command.add_field(name="list", value="Reveals 10 songs in the queue at where the current song is at including itself \n(channel: ALL)",inline=False)
        await ctx.respond(embed=embed_musicplayer_command)

#add extension commands for bot
def setup(bot):
    bot.add_cog(help_log(bot))