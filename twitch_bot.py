from twitchio.ext import commands
import asyncio
import re
import random
from osu_manager import OsuManager

class Bot(commands.Bot):
    def __init__(self, token, channel, app_callback, allowed_domains, osu_config):
        # Очищаем токен от префикса oauth:, если он есть
        clean_token = token.replace('oauth:', '').strip()
        
        # Инициализируем родительский класс twitchio
        super().__init__(token=clean_token, prefix='!', initial_channels=[channel])
        
        self.app_callback = app_callback
        self.channel_name = channel
        self.loop = None # Будет задан из app.py
        self.osu_config_ref = osu_config
        
        # Инициализируем менеджер osu!
        self.osu = OsuManager(
            client_id=osu_config.get('osu_client_id'),
            client_secret=osu_config.get('osu_client_secret'),
            username=osu_config.get('osu_username')
        )
        self.current_skin = "Стандартный (Измени через !setskin)"

    async def event_ready(self):
        print(f"✅ Успешный вход в чат: {self.nick}")
        # Получаем API токен osu! при запуске
        try:
            await self.osu.get_token()
            print("✅ Токен osu! API получен")
        except Exception as e:
            print(f"❌ Ошибка получения токена osu!: {e}")

    async def send_chat_message(self, message_text):
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(message_text)

    # --- КОМАНДЫ ЧАТА ---

    @commands.command(name='skin', aliases=['скин'])
    async def skin_command(self, ctx):
        await ctx.send(f"🎨 Скин: {self.current_skin}")

    @commands.command(name='setskin')
    async def set_skin_command(self, ctx):
        # Только для модераторов и стримера
        if ctx.author.is_mod or ctx.author.name.lower() == self.channel_name.lower():
            self.current_skin = ctx.message.content.replace("!setskin", "").strip()
            await ctx.send("✅ Скин обновлен!")

    @commands.command(name='stats', aliases=['rank'])
    async def stats_command(self, ctx):
        stats = await self.osu.get_user_stats()
        if stats:
            await ctx.send(f"📊 {stats['username']}: #{stats['rank']} | {stats['pp']}pp | {round(stats['acc'], 2)}%")

    @commands.command(name='roll')
    async def roll_command(self, ctx):
        parts = ctx.message.content.split()
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 100
        await ctx.send(f"🎲 {ctx.author.name}: {random.randint(1, limit)}")

    # --- ОБРАБОТКА СООБЩЕНИЙ ---

    async def event_message(self, message):
        # Игнорируем сообщения от самого бота
        if message.echo:
            return

        # Сначала проверяем, не команда ли это
        await self.handle_commands(message)

        content = message.content
        beatmap_id = None
        
        # Регулярные выражения для поиска ссылок на карты
        match_set = re.search(r'osu\.ppy\.sh/beatmapsets/\d+#osu/(\d+)', content)
        match_simple = re.search(r'osu\.ppy\.sh/(?:b|beatmaps)/(\d+)', content)

        if match_set:
            beatmap_id = match_set.group(1)
        elif match_simple:
            beatmap_id = match_simple.group(1)
        
        if beat
