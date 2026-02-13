from twitchio.ext import commands
import asyncio
import re
import random
from osu_manager import OsuManager

class Bot(commands.Bot):
    def __init__(self, token, channel, app_callback, osu_config):
        clean_token = token.replace('oauth:', '').strip()
        super().__init__(token=f"oauth:{clean_token}", prefix='!', initial_channels=[channel])
        
        self.app_callback = app_callback
        self.channel_name = channel
        self.osu = OsuManager(
            client_id=osu_config.get('osu_client_id'),
            client_secret=osu_config.get('osu_client_secret'),
            username=osu_config.get('osu_username')
        )
        self.current_skin = "Стандартный"

    async def event_ready(self):
        print(f"✅ Бот залогинился как: {self.nick}")
        await self.osu.get_token()

    @commands.command(name='roll')
    async def roll_command(self, ctx):
        num = random.randint(1, 100)
        await ctx.send(f"🎲 {ctx.author.name} выкинул {num}!")

    @commands.command(name='skin')
    async def skin_command(self, ctx):
        await ctx.send(f"🎨 Текущий скин: {self.current_skin}")

    async def event_message(self, message):
        if message.echo: return

        # Обработка команд (!roll и т.д.)
        await self.handle_commands(message)

        # Поиск ссылок osu!
        content = message.content
        # Регулярка ловит: /b/ID, /beatmaps/ID, /beatmapsets/ID#osu/ID
        regex = r"osu\.ppy\.sh/(?:beatmapsets/\d+#osu|b|beatmaps)/(\d+)"
        match = re.search(regex, content)

        if match:
            beatmap_id = match.group(1)
            print(f"🔎 Найдена карта ID: {beatmap_id}")
            map_info = await self.osu.get_beatmap_info(beatmap_id)
            if map_info and self.app_callback:
                self.app_callback(message.author.name, map_info, content)
