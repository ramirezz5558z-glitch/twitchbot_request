import aiohttp

class OsuManager:
    def __init__(self, client_id, client_secret, username):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.access_token = None
        self.user_id = None
        self.base_url = "https://osu.ppy.sh/api/v2"

    async def get_token(self):
        url = "https://osu.ppy.sh/oauth/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "public"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    res = await resp.json()
                    self.access_token = res.get("access_token")
                    return self.access_token
        except: return None

    async def get_user_id(self):
        if self.user_id: return self.user_id
        if not self.access_token: await self.get_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/users/{self.username}/osu", headers=headers) as resp:
                    if resp.status != 200: return None
                    data = await resp.json()
                    self.user_id = data.get("id")
                    return self.user_id
        except: return None

    async def get_user_stats(self):
        if not self.access_token: await self.get_token()
        if not self.user_id: await self.get_user_id()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/users/{self.user_id}/osu", headers=headers) as resp:
                    data = await resp.json()
                    stats = data.get("statistics", {})
                    return { "username": data.get("username"), "rank": stats.get("global_rank"), "pp": stats.get("pp"), "acc": stats.get("hit_accuracy") }
        except: return None

    async def get_beatmap_info(self, beatmap_id):
        if not self.access_token: await self.get_token()
        u_id = await self.get_user_id()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            try:
                # Получаем данные карты
                async with session.get(f"{self.base_url}/beatmaps/{beatmap_id}", headers=headers) as r:
                    if r.status != 200:
                         return {"map_name": "Карта не найдена", "text": "Неверный ID", "bg_url": "https://osu.ppy.sh/images/layout/beatmaps/default-bg.jpg", "stars": 0}
                    b_data = await r.json()
                
                # Получаем скор (если есть)
                s_data = {}
                if u_id:
                    async with session.get(f"{self.base_url}/beatmaps/{beatmap_id}/scores/users/{u_id}/all", headers=headers) as r:
                        if r.status == 200: s_data = await r.json()
                
                return self.parse_data(b_data, s_data)
            except Exception as e:
                print(f"API Error: {e}")
                return {"map_name": "Ошибка API", "text": "Сбой", "bg_url": "https://osu.ppy.sh/images/layout/beatmaps/default-bg.jpg", "stars": 0}

    def parse_data(self, b_data, s_data):
        set_data = b_data.get("beatmapset", {}) or {}
        
        # === ЖЕЛЕЗОБЕТОННАЯ ЛОГИКА КАРТИНОК ===
        # Мы сами собираем ссылку, не надеясь на API
        beatmapset_id = set_data.get("id")
        
        if beatmapset_id:
            # Ссылка на официальные ассеты. Работает всегда.
            bg_url = f"https://assets.ppy.sh/beatmaps/{beatmapset_id}/covers/card.jpg"
        else:
            # Если ID нет - дефолт
            bg_url = "https://osu.ppy.sh/images/layout/beatmaps/default-bg.jpg"
        # ======================================

        map_name = f"{set_data.get('title', 'Unknown')} [{b_data.get('version', '?')}]"
        stars = b_data.get("difficulty_rating", 0)
        
        scores = s_data.get("scores", [])
        if not scores:
            return {"map_name": map_name, "bg_url": bg_url, "text": "🆕 Карта еще не сыграна", "stars": stars}

        best = scores[0]
        acc = round(best.get("accuracy", 0) * 100, 2)
        pp = best.get("pp")
        pp_str = f"{round(pp)}pp" if pp else "0pp"
        
        mods_list = best.get("mods", [])
        mods_str = ""
        if mods_list:
            if isinstance(mods_list[0], str): mods_str = " +" + "".join(mods_list)
            else: mods_str = " +" + "".join([m.get("acronym", "") for m in mods_list])

        return {
            "map_name": map_name,
            "bg_url": bg_url,
            "text": f"🏆 {acc}% | {pp_str} | {best.get('rank')}{mods_str} | {best.get('max_combo')}x",
            "stars": stars
        }
import aiohttp

class OsuManager:
    def __init__(self, client_id, client_secret, username):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.access_token = None
        self.user_id = None
        self.base_url = "https://osu.ppy.sh/api/v2"

    async def get_token(self):
        url = "https://osu.ppy.sh/oauth/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "public"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    res = await resp.json()
                    self.access_token = res.get("access_token")
                    return self.access_token
        except: return None

    async def get_user_id(self):
        if self.user_id: return self.user_id
        if not self.access_token: await self.get_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/users/{self.username}/osu", headers=headers) as resp:
                    if resp.status != 200: return None
                    data = await resp.json()
                    self.user_id = data.get("id")
                    return self.user_id
        except: return None

    async def get_user_stats(self):
        if not self.access_token: await self.get_token()
        if not self.user_id: await self.get_user_id()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/users/{self.user_id}/osu", headers=headers) as resp:
                    data = await resp.json()
                    stats = data.get("statistics", {})
                    return { "username": data.get("username"), "rank": stats.get("global_rank"), "pp": stats.get("pp"), "acc": stats.get("hit_accuracy") }
        except: return None

    async def get_beatmap_info(self, beatmap_id):
        if not self.access_token: await self.get_token()
        u_id = await self.get_user_id()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            try:
                # Получаем данные карты
                async with session.get(f"{self.base_url}/beatmaps/{beatmap_id}", headers=headers) as r:
                    if r.status != 200:
                         return {"map_name": "Карта не найдена", "text": "Неверный ID", "bg_url": "https://osu.ppy.sh/images/layout/beatmaps/default-bg.jpg", "stars": 0}
                    b_data = await r.json()
                
                # Получаем скор (если есть)
                s_data = {}
                if u_id:
                    async with session.get(f"{self.base_url}/beatmaps/{beatmap_id}/scores/users/{u_id}/all", headers=headers) as r:
                        if r.status == 200: s_data = await r.json()
                
                return self.parse_data(b_data, s_data)
            except Exception as e:
                print(f"API Error: {e}")
                return {"map_name": "Ошибка API", "text": "Сбой", "bg_url": "https://osu.ppy.sh/images/layout/beatmaps/default-bg.jpg", "stars": 0}

    def parse_data(self, b_data, s_data):
        set_data = b_data.get("beatmapset", {}) or {}
        
        # === ЖЕЛЕЗОБЕТОННАЯ ЛОГИКА КАРТИНОК ===
        # Мы сами собираем ссылку, не надеясь на API
        beatmapset_id = set_data.get("id")
        
        if beatmapset_id:
            # Ссылка на официальные ассеты. Работает всегда.
            bg_url = f"https://assets.ppy.sh/beatmaps/{beatmapset_id}/covers/card.jpg"
        else:
            # Если ID нет - дефолт
            bg_url = "https://osu.ppy.sh/images/layout/beatmaps/default-bg.jpg"
        # ======================================

        map_name = f"{set_data.get('title', 'Unknown')} [{b_data.get('version', '?')}]"
        stars = b_data.get("difficulty_rating", 0)
        
        scores = s_data.get("scores", [])
        if not scores:
            return {"map_name": map_name, "bg_url": bg_url, "text": "🆕 Карта еще не сыграна", "stars": stars}

        best = scores[0]
        acc = round(best.get("accuracy", 0) * 100, 2)
        pp = best.get("pp")
        pp_str = f"{round(pp)}pp" if pp else "0pp"
        
        mods_list = best.get("mods", [])
        mods_str = ""
        if mods_list:
            if isinstance(mods_list[0], str): mods_str = " +" + "".join(mods_list)
            else: mods_str = " +" + "".join([m.get("acronym", "") for m in mods_list])

        return {
            "map_name": map_name,
            "bg_url": bg_url,
            "text": f"🏆 {acc}% | {pp_str} | {best.get('rank')}{mods_str} | {best.get('max_combo')}x",
            "stars": stars
        }

