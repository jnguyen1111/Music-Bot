import discord
import yt_dlp
from discord import FFmpegPCMAudio
from discord.ext import commands
from googleapiclient.discovery import build
import random
import  asyncio

class music_player_commands(commands.Cog):
    def __init__(self ,bot):
        self.bot = bot
        self.song_index = 0
        self.song_audio_list = []
        self.song_title_list = []
        self.song_thumbnail_list = []
        self.queue_at_end = False       #If the queue is at the end, we allow new songs to be added and played instantly
        self.seek_song = False          #allows goto function to work and seek specific song
        self.song_first = True          #allows the play command to either play first song that is queued into the list
        self.song_replay = False        #allows song to be looped
        self.song_add = False           #when final song ends allows user to add and play the next song added
        self.song_clear = False         #allows dc and clear to work properly
        self.song_chosen = None         #song chosen to be played
        self.is_playlist = False        #checks if link is a playlist url if so convert the url so it can download the playlist
        self.is_mix_playlist = False    #checks if the link is a mixed playlist
        self.final_url_link = None      #final url link before we pass it into the obtain song info function to download the song/playlist
        self.url_template = "https://www.youtube.com/watch"   #checks if url user passes is a valid link
        self.url_already_playlist_template = "https://www.youtube.com/playlist?list=" #if its already a proper playlist url do not convert the url string
        self.url_mixed_playlist_template = "list=RD" #used to detect if the link is a mixed playlist
        self.user_not_in_channel_error = "You need to be in a voice channel to use this command"
        self.bot_not_in_channel_error ="Error Bot is not in voice channel!"
        self.youtube_api_key = bot.youtube_api_key
        self.youtube_api_service_name = "youtube"
        self.youtube_api_version = "v3"

    # #cleans up music player data to a clean state
    def clear_data(self):
        self.song_index = 0
        self.song_audio_list.clear()
        self.song_title_list.clear()
        self.song_thumbnail_list.clear()
        self.queue_at_end = False
        self.seek_song = False
        self.song_first = True
        self.song_replay = False
        self.song_add = False
        self.song_clear = True  #set to be true to stop the autoplay function
        self.song_chosen = None

    #obtain user id and format it to be able to mention user
    async def obtain_user_tag(self,ctx):
        return '<@' + str(ctx.author.id) + '>'

    #obtain current voice channel of the bot
    async def obtain_bot_voice_channel(self,ctx):
        return discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

     #shutdown the bot and ends the program
    @discord.slash_command(name="shutdownbot")
    async def shut_down_bot(self, ctx):
        user = await self.obtain_user_tag(ctx)
        bot_voice_channel = await self.obtain_bot_voice_channel(ctx)
        if bot_voice_channel and bot_voice_channel.is_connected():
            self.clear_data()
            await bot_voice_channel.disconnect()
        await ctx.respond(f"Shutting down music bot... {user}")
        exit(-1)

    #cleans up musicplayer to clean state  and disconnects bot
    @discord.slash_command(name="dc")
    async def disconnect_music(self,ctx):
        user = await self.obtain_user_tag(ctx)
        bot_voice_channel = await self.obtain_bot_voice_channel(ctx)
        user_voice_channel = ctx.author.voice
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        elif bot_voice_channel and bot_voice_channel.is_connected():
            self.clear_data()
            bot_voice_channel.stop()
            await bot_voice_channel.disconnect()
            await ctx.respond(f"{self.bot.user.name} has disconnected {user}")
        else:
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")

    #cleans up music player
    @discord.slash_command(name="clear")
    async def clean_info(self,ctx):
        user = await self.obtain_user_tag(ctx)
        bot_voice_channel = await self.obtain_bot_voice_channel(ctx)
        user_voice_channel = ctx.author.voice
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        elif bot_voice_channel and bot_voice_channel.is_connected():
            self.clear_data()
            bot_voice_channel.stop()
            await ctx.respond(f"Clearing song list, requested by {user}")
        else:
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")

    # load a song from audio list url into ffmpeg to play audio and when song ends call the  autoplay function
    def load_player(self, choose_song, voice):
        FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}
        voice.play(FFmpegPCMAudio(choose_song, **FFMPEG_OPTS, executable="C:/ffmpeg/bin/ffmpeg.exe"),after=lambda choose_song: self.auto_play(voice))

    def auto_play(self, voice):
        # at the end of the queuelist load the song
        if self.queue_at_end:
            self.load_player(self.song_chosen,voice)
            self.song_add = False
            self.queue_at_end = False
        #seeks specific song from goto function
        elif self.seek_song:
            self.load_player(self.song_chosen,voice)
            self.song_add = False
            self.seek_song = False
        #if we are at the end of the song queue list and theres not a loop we trigger the voice to stop
        #and set the condition to where if we add a new song it will autoplay
        elif self.song_index == len(self.song_title_list)-1 and not self.song_replay:
            self.song_add = True
            voice.stop()
        # allows current song to loop if condition is met
        elif self.song_replay and voice.is_playing() == False:
            voice.stop()
            self.song_chosen = self.song_audio_list[self.song_index]
            self.load_player(self.song_chosen, voice)
        # autoplay feature which plays next song
        elif voice.is_playing() == False and voice.is_paused() == False and self.song_replay == False:
            voice.stop()
            # when clear or dc is called the song is stopped which calls autoplay which we dont load any songs into the player
            if not self.song_clear:
                # if we are not at the end of the song queue update index
                #if we are just play the song we have just added
                if (not self.song_add):
                    self.song_index += 1
                #load the next song into the player
                self.song_chosen = self.song_audio_list[self.song_index]
                self.load_player(self.song_chosen, voice)

    #extract entries of playlist/mix
    def extractPlaylist(self,info):
        playlist_data = info.get("entries")
        if self.is_playlist:
            for item in playlist_data:
                self.song_title_list.append(item["fulltitle"])
                self.song_thumbnail_list.append(item["thumbnails"][len(info["thumbnails"]) - 1]["url"])
                self.song_audio_list.append(item["url"])
        elif self.is_mix_playlist:
            for item in playlist_data:
                self.song_title_list.append(item["fulltitle"])
                self.song_thumbnail_list.append(item["thumbnail"])
                self.song_audio_list.append(item["url"])

    #extracts song/playlist from url user  provided
    def obtain_song_info(self, link):
        ydl_opts = {
            'format': 'bestaudio'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
        #if link is playlist or mixed playlist call function to extract data
        if self.is_playlist or self.is_mix_playlist:
            self.extractPlaylist(info)
        #extract single song link
        else:
            self.song_title_list.append(info["fulltitle"])
            self.song_thumbnail_list.append(info["thumbnails"][len(info["thumbnails"])-1]["url"])
            self.song_audio_list.append(info["url"])

    #finds youtube video id for specific song request
    def find_video_id(self,songname):
        videos = []
        youtube = build(self.youtube_api_service_name, self.youtube_api_version, developerKey=self.youtube_api_key)
        search_response = youtube.search().list(
            q=f"{songname} lyrics",
            part='snippet',
            maxResults=5
        ).execute()
        for search_result in search_response.get('items', []):
            # parse into the id key and check if its a youtube video if it is grab the video ID
            if search_result['id']['kind'] == 'youtube#video':
                videos.append('%s' % (search_result['id']['videoId']))
        return self.url_template + "?v=" + videos[random.randint(0, len(videos) - 1)]

    #searches song user requests and adds it to the queue
    @discord.slash_command(name="searchsong")
    async def find_song(self,ctx,songname):
        # create event loop object runs aynch tasks and run subprocesses
        loop = asyncio.get_event_loop()
        final_link = await loop.run_in_executor(None, self.find_video_id, songname)
        await self.queue_music(ctx,final_link)

    # checks link specified and returns true if the link provided is valid
    async def is_link_valid(self, user, ctx, link):
        if self.url_template not in link:
            await ctx.respond(f"Invalid link, please provide a youtube url link to a video or a playlist! {user}")
            return False
        elif self.url_mixed_playlist_template in link:
            self.is_mix_playlist = True
            self.final_url_link = link
            await ctx.respond(
                f"Mixed Playlist link found converting link... It may take a while grab your popcorn cat. {user}")
            return True
        # if the link is a playlist and its not in proper url form convert the link and send it through  or else leave it as is
        elif (self.url_already_playlist_template not in link and "list" in link):
            self.final_url_link = link[link.find("https"):link.find("watch")] + "playlist?" + link[link.find("&list"):]
            self.is_playlist = True
            await ctx.respond(
                f"Playlist link found converting link... It may take a while grab your popcorn cat. {user}")
            return True
        else:
            self.final_url_link = link
            return True
        return False

    #plays song/playlist requested by user
    @discord.slash_command(name="queue")
    async def queue_music(self, ctx, link):
        self.song_clear = False
        self.song_replay = False
        self.queue_at_end = False
        self.seek_song = False
        voice = await self.obtain_bot_voice_channel(ctx)
        user = await self.obtain_user_tag(ctx)
        user_voice_channel = ctx.author.voice.channel

        #if link is invalid sotp the command from processing any further
        if not await self.is_link_valid(user,ctx,link):
            return None
        #if user not in voice channel or theres a invalid link notify the user
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None

        #create event loop object runs aynch tasks and run subprocesses
        loop = asyncio.get_event_loop()

        #first song condition add and play it  or if at the end of the playlist queue the song/playlist and automatically play it
        if self.song_first or self.song_add:
            try:
                if (self.song_add):
                    self.song_add = False
                    self.song_index += 1
                await loop.run_in_executor(None,self.obtain_song_info,self.final_url_link)
                self.song_chosen = self.song_audio_list[self.song_index]

                if voice and voice.is_connected():
                    await voice.move_to(user_voice_channel)
                else:
                    voice = await user_voice_channel.connect()
                self.load_player(self.song_chosen, voice)
                self.song_first = False
                await ctx.respond(f"Now playing: {self.song_title_list[self.song_index]}, requested by {user}")
            except Exception as e:
                print(e)
                await ctx.respond(f"There was an Error processing your request, !fishpain {user}")
        else:
            await loop.run_in_executor(None, self.obtain_song_info, self.final_url_link)
            if self.is_playlist or self.is_mix_playlist:
                await ctx.respond(f"Adding  requested playlist/mix to the queue requested by {user}")
            else:
                await ctx.respond(f"Adding {self.song_title_list[len(self.song_title_list)-1]}, requested by {user}")

        #reset mix/playlist flag after finishing processing
        self.is_playlist = False
        self.is_mix_playlist = False

    #seek to a specific index the User requests
    @discord.slash_command(name="goto")
    async def skip_to_song_index(self,ctx,index_requested):
        self.song_clear = False
        self.song_replay = False
        voice = await self.obtain_bot_voice_channel(ctx)
        user = await self.obtain_user_tag(ctx)
        user_voice_channel = ctx.author.voice.channel

        # if user not in voice channel or theres a invalid link notify the user
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        if not voice.is_connected():
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")
            return None
        #if invalid index or user not in voice or bot is not connected to voice channel or empty queue notify user invalid request
        if(len(self.song_audio_list) == 0):
            await ctx.send(f"Error, empty queuelist! {user}")
            return None
        elif(int(index_requested) < 0 or int(index_requested) >= len(self.song_audio_list)):
            await ctx.respond(f"Error, Invalid Index range please specify a valid Index to go to in the playlist queue {user}")
            return None
            # Exiting if the user is not in a voice channel

        #request last song in queuelist set flag
        if(int(index_requested) == len(self.song_audio_list)-1):
            self.queue_at_end = True
        else:
            self.seek_song = True

        self.song_index = int(index_requested)
        self.song_chosen = self.song_audio_list[self.song_index]
        voice.stop()
        if(self.song_add):
            self.load_player(self.song_chosen,voice)
        await ctx.respond(f"Now playing: {self.song_title_list[self.song_index]}, requested by {user}")

    #move on to the next song in the playlist and load into the player
    @discord.slash_command(name="skip")
    async def next_song(self,ctx):
        self.song_replay = False
        voice = await self.obtain_bot_voice_channel(ctx)
        user = await self.obtain_user_tag(ctx)
        user_voice_channel = ctx.author.voice.channel

        # if user not in voice channel or theres a invalid link notify the user
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        else:
            self.queue_at_end = False
            self.seek_song = False
            voice.stop()
            self.song_chosen = self.song_audio_list[self.song_index]
            if self.song_index < (len(self.song_title_list) - 1):
                await ctx.respond(f"Now playing: {self.song_title_list[self.song_index + 1]}, requested by {user}")

    #plays previous song in queue if theres only one song or the song is the first index replay it
    @discord.slash_command(name="previous")
    async def previous_song(self, ctx):
        voice = await self.obtain_bot_voice_channel(ctx)
        user = await self.obtain_user_tag(ctx)
        user_voice_channel = ctx.author.voice.channel

        # if user not in voice channel or theres a invalid link notify the user
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        if not voice.is_connected():
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")
            return None
        self.song_replay = False
        self.song_index -= 2
        self.queue_at_end = False
        self.seek_song = False
        voice.stop()

        # allows last song to be played when last song ended condition for only two songs in queue
        if self.song_add and self.song_index > 1:
            self.song_add = False
            self.song_index += 1
            self.song_chosen = self.song_audio_list[self.song_index]
            self.load_player(self.song_chosen, voice)
            await ctx.respond(f"Now playing: {self.song_title_list[self.song_index]}, requested by {user}")

        # allows last song to be played back when last song ended
        elif self.song_add:
            self.song_add = False
            self.song_index += 2
            self.song_chosen = self.song_audio_list[self.song_index]
            self.load_player(self.song_chosen, voice)
            await ctx.respond(f"Now playing: {self.song_title_list[self.song_index]}, requested by {user}")

        # When index is first song and previous is called replay first song
        elif self.song_index <= -1:
            self.song_index = -1
            self.song_chosen = self.song_audio_list[self.song_index]
            voice.stop()
            await ctx.respond(f"Now playing: {self.song_title_list[self.song_index + 1]}, requested by {user}")
        # When conditions above does not meet it just plays previous song depending on the index - 1
        else:
            self.song_chosen = self.song_audio_list[self.song_index]
            voice.stop()
            await ctx.respond(f"Now playing: {self.song_title_list[self.song_index + 1]}, requested by {user}")

    #loops current song
    @discord.slash_command(name="loop")
    async def loop_song(self,ctx):
        self.song_clear = False
        self.queue_at_end = False
        self.seek_song = False
        self.song_replay = True
        user = await self.obtain_user_tag(ctx)
        voice = await self.obtain_bot_voice_channel(ctx)
        user_voice_channel = ctx.author.voice.channel
        # Exiting if the user is not in a voice channel
        # if user not in voice channel or theres a invalid link notify the user
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        if not voice.is_connected():
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")
            return None
        await ctx.respond(f"Looping {self.song_title_list[self.song_index]}, requested by {user}")

    #pauses current song
    @discord.slash_command(name="pause")
    async def pause_music(self,ctx):
        voice_state = ctx.author.voice
        voice = await self.obtain_bot_voice_channel(ctx)
        user = await self.obtain_user_tag(ctx)
        user_voice_channel = ctx.author.voice.channel
        # Exiting if the user is not in a voice channel
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        if not voice.is_connected():
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")
            return None
        voice.pause()
        await ctx.respond(f"Music player has paused. {user}")

    #resumes the current song
    @discord.slash_command(name="resume")
    async def resume_music(self,ctx):
        voice_state = ctx.author.voice
        user = await self.obtain_user_tag(ctx)
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        user_voice_channel = ctx.author.voice.channel
        if user_voice_channel is None:
            await ctx.respond(f"{self.user_not_in_channel_error} {user}")
            return None
        if not voice.is_connected():
            await ctx.respond(f"{self.bot_not_in_channel_error} {user}")
            return None
        voice.resume()
        await ctx.respond(f"Music player has resumed. {user}")

    #gets the current song play if possible
    @discord.slash_command(name="current")
    async def current_song(self,ctx):
        embed_color = discord.Colour.red()
        #No song are currently playing
        if self.song_add or len(self.song_audio_list) == 0:
            currentsong_embed = discord.Embed(title="Current Song", description= "No song is currently playing",color=embed_color)
            currentsong_embed.set_footer(text="requested by {}".format("@" + ctx.author.display_name))
        #Gets current song that is playing
        else:
            currentsong_embed = discord.Embed(title="Current Song", description = self.song_title_list[self.song_index], color=embed_color)
            currentsong_embed.set_thumbnail(url = self.song_thumbnail_list[self.song_index])
            currentsong_embed.set_footer(text = "requested by {}".format("@" + ctx.author.display_name) )
        await ctx.respond(embed = currentsong_embed)

    #create the queuelist embed
    def create_queue_embed(self , queue , start_index , end_index):
         for track in range(start_index, end_index):
             #find the index the current track is playing and mark it as the current song else print out the song title
             if track == self.song_index:
                 current_song = str(("""```diff\n{}) {}<-CURRENT SONG\n```""").format(track, self.song_title_list[track]))
                 queue.add_field(name="\u200b", value=current_song,inline=False)
             else:
                 queue.add_field(name="\u200b", value="{}) {}\n".format(track, self.song_title_list[track]),inline=False)
         # show the size of the playlist
         queue.add_field(name="\u200b", value=f"PLAYLIST QUEUE SIZE: {len(self.song_audio_list)}", inline=False)
         return queue

    # define a function to reduce multiple for loops
    @discord.slash_command(name="list")
    async def current_queue(self,ctx):
        embed_color = discord.Colour.purple()

        #if there is no songs then display empty list
        if  len(self.song_audio_list) == 0 or self.song_add:
            queue_list = discord.Embed(title="Queue List (No songs)", color=embed_color)
            queue_list.set_thumbnail(url="https://media.tenor.com/tlMYoqV4neoAAAAd/cat-bored.gif")
            queue_list.add_field(name="\u200b", value="There are no songs in queue.", inline=True)
            queue_list.set_footer(text="Use /queue to add a song/playlist/mix into the queue.")
            await ctx.respond(embed = queue_list)
        else:
            queue_embed = discord.Embed(title="Queue List", color=embed_color)
            queue_embed.set_thumbnail(url="https://media.tenor.com/Qrq6rq8enxUAAAAd/cats-vibe-cats.gif")
            queue_embed.add_field(name="\u200b", value="Indexes by numbers.", inline=True)

            # when song index is 0 and we have over ten songs, we want to get 10 songs in queue to display to user
            if len(self.song_title_list) > 10 and self.song_index == 0:
                queue_list = self.create_queue_embed(queue_embed, self.song_index, (self.song_index + 10))

            # when the song index is not zero and we have over ten songs we display relative to the song index next ten songs
            elif self.song_index > 0 and (self.song_index + 10) < len(self.song_title_list) and len(self.song_title_list) > 10:
                queue_list = self.create_queue_embed(queue_embed, (self.song_index - 1), (self.song_index + 10))

            #when the queue list which is greater than 10 is shrinking we display the remaining songs
            elif len(self.song_title_list) > 10 :
                queue_list = self.create_queue_embed(queue_embed, (self.song_index - 1), len(self.song_title_list))

            #when the queue is less than 10 and song index is at 0 send the embed corresponding to condition
            if self.song_index == 0 and len(self.song_title_list) < 10:
                queue_list = self.create_queue_embed(queue_embed, self.song_index, len(self.song_title_list))

            #when song index is not 0 and queue is less than 10 send the queuelist relative to the song index
            elif self.song_index > 0 and len(self.song_title_list) < 10:
                queue_list = self.create_queue_embed(queue_embed, (self.song_index - 1), len(self.song_title_list))
            await ctx.respond(embed=queue_list)

# add command extension to the bot
def setup(bot):
    bot.add_cog(music_player_commands(bot))




