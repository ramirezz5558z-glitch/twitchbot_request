from twitchio.ext import commands
import asyncio
import re
import random
from osu_manager import OsuManager

class Bot(commands.Bot):
    def __init__(self, token, channel, app_callback, allowed_domains, osu_config):
        clean_token = token.replace('oauth:', '').strip()
        super().__init__(token=clean_token, prefix='!', initial_channels=[channel])
        self.app_callback = app_callback
        self.channel_name = channel
        self.loop = None
        self.osu_config_ref = osu_config
        self.osu = OsuManager(
            client_id=osu_config.get('osu_client_id'),
            client_secret=osu_config.get('osu_client_secret'),
            username=osu_config.get('osu_username')
        )
        self.current_skin = "Стандартный (Измени через !setskin)"

    async def event_ready(self):
        print(f"✅ Успешный вход в чат: {self.nick}")
        await self.osu.get_token()

    async def send_chat_message(self, message_text):
        channel = self.get_channel(self.channel_name)
        if channel: await channel.send(message_text)

    # --- КОМАНДЫ ---

    @commands.command(name='skin', aliases=['скин'])
    async def skin_command(self, ctx):
        await ctx.send(f"🎨 Скин: {self.current_skin}")

    @commands.command(name='setskin')
    async def set_skin_command(self, ctx):
        if ctx.author.is_mod:
            self.current_skin = ctx.message.content.replace("!setskin", "").strip()
            await ctx.send("✅ Скин обновлен!")

    @commands.command(name='stats', aliases=['rank'])
    async def stats_command(self, ctx):
        stats = await self.osu.get_user_stats()
        if stats: await ctx.send(f"📊 {stats['username']}: #{stats['rank']} | {stats['pp']}pp | {round(stats['acc'], 2)}%")

    @commands.command(name='roll')
    async def roll_command(self, ctx):
        parts = ctx.message.content.split()
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 100
        await ctx.send(f"🎲 {ctx.author.name}: {random.randint(1, limit)}")

    async def event_message(self, message):
        if message.echo: return
        await self.handle_commands(message)

        content = message.content
        beatmap_id = None
        
        match_set = re.search(r'osu\.ppy\.sh/beatmapsets/\d+#osu/(\d+)', content)
        match_simple = re.search(r'osu\.ppy\.sh/(?:b|beatmaps)/(\d+)', content)

        if match_set: beatmap_id = match_set.group(1)
        elif match_simple: beatmap_id = match_simple.group(1)
        
        if beatmap_id:
            try:
                osu_data = await self.osu.get_beatmap_info(beatmap_id)
                
                # Получаем настройки
                min_sr = float(self.osu_config_ref.get('min_sr', 0) or 0)
                max_sr = float(self.osu_config_ref.get('max_sr', 20) or 20)
                
                # Получаем сырое число звезд
                raw_sr = float(osu_data.get('stars', 0))
                
                # Форматируем красиво: 6.453 -> "6.5"
                sr_str = f"{raw_sr:.1f}" 
                
                if raw_sr < min_sr or raw_sr > max_sr:
                    await self.send_chat_message(f"@{message.author.name} ❌ {sr_str}⭐ (Лимит: {min_sr}-{max_sr})")
                    return

                # Отправляем в чат
                await self.send_chat_message(f"@{message.author.name} [{osu_data['map_name']}] ({sr_str}⭐) -> {osu_data['text']}")
                
                # Отправляем в Дэшборд
                self.app_callback(message.author.name, {
                    "full_msg": content, 
                    # ВОТ ТУТ ГЛАВНОЕ ИСПРАВЛЕНИЕ: Используем красивую строку sr_str
                    "map_name": f"[{sr_str}⭐] " + osu_data['map_name'], 
                    "bg_url": osu_data['bg_url']
                })
            except Exception as e:
                print(f"❌ Ошибка: {e}")


