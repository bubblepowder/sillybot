import asyncio
import discord
import youtube_dl

from discord.ext import commands


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, url):

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        await ctx.send(f':play_pause: **Now playing:** {player.title}')
        print('A user is playing a song')

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("**:no_entry_sign: You are not connected to a voice channel.**")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):

        await ctx.voice_client.disconnect()
        await ctx.send(f'**:cloud: Silly Bot has stopped.**')
        print('A user has stopped the bot')

    @commands.command()
    async def leave(self, ctx):

        await ctx.voice_client.disconnect()
        await ctx.send(f'**:cloud: Silly Bot has left the voice channel.**')
        print('A user has stopped the bot')

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("**:no_entry_sign: You are not connected to a voice channel.**")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

bot = commands.Bot(command_prefix=commands.when_mentioned_or("silly!"), description='Relatively simple music bot example', help_command=None)

@bot.command()
async def help(ctx):
    await ctx.send(f"> :wave: Welcome to the **Silly Bot** you are in **{ctx.message.guild.name}**, \n > :computer: **Commands:** \n > :play_pause: Play Music: `silly!play (Name or URL of Video/Stream)` \n > :play_pause: Stop the Bot: `silly!stop` \n > :loud_sound: Change the Volume: `silly!volume (Level of Volume 0/100)`")

@bot.command()
async def join(ctx):
    await ctx.send(f":no_entry_sign: Use the `silly!play (Name or URL of Video/Stream)` command to have **SillyBot** join your voice channel and play music. Use the `silly!help` command for more help")

@bot.event
async def on_ready():
    print('Logged in as:')
    print(bot.user.name)
    print(' ')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="the abyss | silly!help"))
    #await bot.change_presence(activity=discord.Streaming(name="My Stream", url=my_twitch_url))
    #await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="a movie"))
    #await bot.change_presence(activity=discord.Game(name="a game"))

bot.add_cog(Music(bot))
bot.run('TOKEN')  # Where 'TOKEN' is your bot token
