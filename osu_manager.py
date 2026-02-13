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
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                res = await resp.json()
                self.access_token = res.get("access_token")
                return self.access_token

    async def get_user_id(self):
        if self.user_id: return self.user_id
        if not self.access_token: await self.get_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/users/{self.username}/osu", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.user_id = data.get("id")
                    return self.user_id
        return None

    async def get_beatmap_info(self, beatmap_id):
        if not self.access_token: await self.get_token()
        u_id = await self.get_user_id()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/beatmaps/{beatmap_id}", headers=headers) as r:
                if r.status != 200: return None
                b_data = await r.json()
                
                # Попробуем найти лучший скор игрока на этой карте
                s_data = {}
                if u_id:
                    async with session.get(f"{self.base_url}/beatmaps/{beatmap_id}/scores/users/{u_id}/all", headers=headers) as r2:
                        if r2.status == 200: s_data = await r2.json()
                
                return self.parse_data(b_data, s_data)

    def parse_data(self, b_data, s_data):
        set_data = b_data.get("beatmapset", {})
        beatmapset_id = set_data.get("id")
        bg_url = f"https://assets.ppy.sh/beatmaps/{beatmapset_id}/covers/card.jpg" if beatmapset_id else ""
        
        map_name = f"{set_data.get('title')} [{b_data.get('version')}]"
        stars = b_data.get("difficulty_rating", 0)
        
        scores = s_data.get("scores", [])
        if not scores:
            text = "🆕 Еще не сыграно"
        else:
            best = scores[0]
            acc = round(best.get("accuracy", 0) * 100, 2)
            pp = round(best.get("pp")) if best.get("pp") else 0
            text = f"🏆 {acc}% | {pp}pp | Rank: {best.get('rank')}"

        return {"map_name": map_name, "bg_url": bg_url, "text": text, "stars": stars}