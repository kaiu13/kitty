import discord
import re
import time
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
client = discord.Client(intents=intents)

spam_tracker = {}
warn_counts = {}
muted_until = {}
SPAM_TIME = 5
SPAM_COUNT = 8

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
    for channel in member.guild.text_channels:
        if channel.permissions_for(member.guild.me).send_messages:
            await channel.send(
                f"welcome, {member.mention} ♡\n"
                "lots of yaps, league, val & wordle\n"
                "czech & english chat\n"
            )
            break

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

    # --- automod: block discord invites and suspicious links ---
    safe_domains = [
        "discord.gg", "discord.com", "youtube.com", "youtu.be",
        "twitter.com", "x.com", "twitch.tv", "instagram.com", "reddit.com"
    ]
    url_match = re.search(r"https?://([a-zA-Z0-9.-]+)", message.content.lower())
    is_invite = re.search(r"(discord\.gg/|discord\.com/invite/)", message.content.lower())
    if url_match or is_invite:
        domain = url_match.group(1) if url_match else ""
        # If it's a discord invite or not a safe domain, delete and mute
        if is_invite or not any(safe in domain for safe in safe_domains):
            await message.delete()
            # Mute immediately for 10 hours
            role = discord.utils.get(message.guild.roles, name="muted")
            if not role:
                role = await message.guild.create_role(name="muted")
                for channel_ in message.guild.channels:
                    await channel_.set_permissions(role, send_messages=False)
            await message.author.add_roles(role)
            muted_until[message.author.id] = time.time() + 10 * 60 * 60  # 10 hours
            await message.channel.send(
                f'{message.author.mention} has been muted for sending a link to chat ♡',
                delete_after=5
            )
            return

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

client.run(os.environ['DISCORD_TOKEN'])