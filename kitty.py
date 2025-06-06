import discord
import re
import time
import os
import asyncio
import random
import aiohttp

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  

spam_tracker = {}
warn_counts = {}
muted_until = {}
SPAM_TIME = 5
SPAM_COUNT = 8

# --- Scheduled posting in #yap every 5 hours ---
async def post_in_yap():
    await client.wait_until_ready()
    while not client.is_closed():
        for guild in client.guilds:
            channel = discord.utils.get(guild.text_channels, name="yap")
            if channel:
                cat_messages = [
                    "https://cataas.com/cat",
                    "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif",
                    "https://i.imgur.com/4AiXzf8.jpg",
                    "cat fact: meow",
                    "https://www.youtube.com/watch?v=5dsGWM5XGdg",
                    "https://media.giphy.com/media/mlvseq9yvZhba/giphy.gif",
                    "show us your cat!",
                    "if you had nine lives, how would you spend them?",
                    "https://i.imgur.com/8bFQw2F.png",
                    "give me a cat confession, hi chat",
                ]
                league_messages = [
                    "how to make ur life easier? if in doubt, blame the jungler (just kidding, not really...)",
                    "i love lux – because sometimes you just want to press R",
                    "hi chat, https://i.imgur.com/8p0hK7F.png",
                    "check out patch notes! https://www.leagueoflegends.com/en-us/news/tags/patch-notes/",
                    "who’s your main in league, drop it below!",
                    "hi chat, https://www.youtube.com/watch?v=BGtROJeMPeE",
                    "if you could delete one champ forever, who would it be?",
                    "let me know ur favorite skin :()",
                    "ranked or ARAM tonight? let us know!",
                ]
                valo_messages = [
                    "who’s your favorite agent?",
                    "i personally hate sage",
                    "what’s your go-to excuse for losing a round?",
                    "if valorant had a cat agent, what would its ability be?",
                ]
                wordle_messages = [
                    "time to blow ur brains out, wordle !! https://www.nytimes.com/games/wordle/index.html",
                    "how did u do that in wordle?",
                    "what's ur starting word in wordle?",
                    "wordle at midnight: the real adulting.",
                ]
                
                # Pick one category at random, then one message from that category
                categories = [
                    cat_messages,
                    league_messages,
                    valo_messages,
                    wordle_messages,
                ]
                chosen_category = random.choice(categories)
                chosen_message = random.choice(chosen_category)
                await channel.send(chosen_message)
        await asyncio.sleep(60 * 60 * 5)  # every 5 hours

class KittyClient(discord.Client):
    async def setup_hook(self):
        self.bg_task = asyncio.create_task(post_in_yap())

client = KittyClient(intents=intents)

@client.event
async def on_ready():
    print(f'♡ {client.user}')
    streaming = discord.Streaming(
        name="kitty",
        url="https://twitch.tv/discord"
    )
    await client.change_presence(activity=streaming)

@client.event
async def on_member_join(member):
    # give "kitty" role if it exists
    role = discord.utils.get(member.guild.roles, name="kitty")
    if role:
        await member.add_roles(role, reason="Autorole on join")
    # Always send welcome in the 'yap' channel
    channel = discord.utils.get(member.guild.text_channels, name="yap")
    if channel and channel.permissions_for(member.guild.me).send_messages:
        await channel.send(
            f"welcome, {member.mention} ♡\n"
            "lots of yaps, league, val & wordle\n"
            "czech & english chat\n"
        )

async def warn_user(user, channel, reason=""):
    user_id = user.id
    warn_counts[user_id] = warn_counts.get(user_id, 0) + 1
    await channel.send(f'{user.mention}, warning {warn_counts[user_id]}/3 for {reason} ♡', delete_after=3)
    if warn_counts[user_id] >= 3:
        role = discord.utils.get(user.guild.roles, name="muted")
        if not role:
            role = await user.guild.create_role(name="muted")
            for channel_ in user.guild.channels:
                await channel_.set_permissions(role, send_messages=False)
        await user.add_roles(role)
        muted_until[user_id] = time.time() + 10 * 60 * 60  # 10 hours
        await channel.send(f'{user.mention} has been muted due to 3 warnings ♡', delete_after=5)
        warn_counts[user_id] = 0  # reset warns
        def is_from_user(m):
            return m.author.id == user_id
        deleted = await channel.purge(limit=20, check=is_from_user)
        await channel.send(f"cleared {len(deleted)} recent messages from {user.mention} ♡", delete_after=2)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_id = message.author.id
    now = time.time()

    # --- unmute if time passed ---
    if user_id in muted_until:
        if now >= muted_until[user_id]:
            role = discord.utils.get(message.guild.roles, name="muted")
            if role and role in message.author.roles:
                await message.author.remove_roles(role)
                await message.channel.send(f'{message.author.mention} has been unmuted ♡', delete_after=3)
            del muted_until[user_id]

    # --- automod: simple spam detection + warn/mute system ---
    spam_tracker.setdefault(user_id, [])
    spam_tracker[user_id] = [t for t in spam_tracker[user_id] if now - t < SPAM_TIME]
    spam_tracker[user_id].append(now)
    if len(spam_tracker[user_id]) > SPAM_COUNT:
        await warn_user(message.author, message.channel, reason="spamming")
        return

    if message.content == 'heart':
        await message.channel.send('♡')

    is_mod = message.author.guild_permissions.manage_messages

    if message.content.startswith('/warn'):
        if is_mod:
            if message.mentions:
                await message.channel.send(f'{message.mentions[0].mention} naughty naughty')
            else:
                await message.channel.send('mention someone to warn')
        else:
            await message.channel.send('nono, u cant do that')

    if message.content.startswith('/mute'):
        if is_mod:
            if message.mentions:
                role = discord.utils.get(message.guild.roles, name="muted")
                if not role:
                    role = await message.guild.create_role(name="muted")
                    for channel in message.guild.channels:
                        await channel.set_permissions(role, send_messages=False)
                await message.mentions[0].add_roles(role)
                await message.channel.send(f'{message.mentions[0].mention} ♡')
            else:
                await message.channel.send('mention someone to mute.')
        else:
            await message.channel.send('nono, u cant do that')

    if message.content.startswith('/unmute'):
        if is_mod:
            if message.mentions:
                role = discord.utils.get(message.guild.roles, name="muted")
                if role:
                    await message.mentions[0].remove_roles(role)
                    await message.channel.send(f'{message.mentions[0].mention} ♡')
                else:
                    await message.channel.send('no muted role found.')
            else:
                await message.channel.send('mention someone to unmute.')
        else:
            await message.channel.send('nono, u cant do that')

    if message.content.startswith('/ban'):
        if is_mod:
            if message.mentions:
                await message.mentions[0].ban()
                await message.channel.send(f'{message.mentions[0].mention} ♡')
            else:
                await message.channel.send('mention someone to ban.')
        else:
            await message.channel.send('nono, u cant do that')

    if message.content.startswith('/clear'):
        if is_mod:
            try:
                amount = int(message.content.split(' ')[1])
            except (IndexError, ValueError):
                amount = 100
            deleted = await message.channel.purge(limit=amount + 1)
            await message.channel.send(f'cleared {len(deleted)-1} messages ♡', delete_after=2)
        else:
            await message.channel.send('nono, u cant do that')

# Map your custom emoji IDs to role names
emoji_to_role = {
    "<:blue:1376550929280794765>": "blue",
    "<:green:1376550931600117850>": "green",
    "<:red:1376550939913359441>": "red",
    "<:lightpink:1376550927850541117>": "lightpink"
}

role_message_id = None  # Will store the ID of the bot's message

@client.event
async def on_ready():
    print(f'♡ {client.user}')
    streaming = discord.Streaming(
        name="kitty",
        url="https://twitch.tv/discord"
    )
    await client.change_presence(activity=streaming)

    # --- Reaction role message setup ---
    global role_message_id
    channel = discord.utils.get(client.get_all_channels(), name="roles")
    if channel:
        async for msg in channel.history(limit=20):
            if msg.author == client.user and "get a role below to customize yourself" in msg.content:
                role_message_id = msg.id
                break
        else:
            msg = await channel.send(
                "get a role below to customize yourself\n"
                "(one reaction at a time)\n"
            )
            role_message_id = msg.id
            for emoji in emoji_to_role:
                await msg.add_reaction(emoji)

@client.event
async def on_raw_reaction_add(payload):
    if payload.message_id != role_message_id:
        return
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return
    emoji_str = str(payload.emoji)
    role_name = emoji_to_role.get(emoji_str)
    if not role_name:
        return
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        return
    member = guild.get_member(payload.user_id)
    if member:
        await member.add_roles(role)

@client.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != role_message_id:
        return
    guild = client.get_guild(payload.guild_id)
    if not guild:
        return
    emoji_str = str(payload.emoji)
    role_name = emoji_to_role.get(emoji_str)
    if not role_name:
        return
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        return
    member = guild.get_member(payload.user_id)
    if member:
        await member.remove_roles(role)

client.run(os.environ['DISCORD_TOKEN'])