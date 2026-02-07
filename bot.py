import os
import asyncio
import datetime
from typing import List

import discord
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_IDS = {int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.isdigit()}
ALLOWED_GUILD_ID = int(os.getenv("ALLOWED_GUILD_ID", "0"))
STATUS_TEXT = os.getenv("STATUS_TEXT", "Broadcast Bot")

if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN")
if not OWNER_IDS:
    raise SystemExit("Missing OWNER_IDS")
if not ALLOWED_GUILD_ID:
    raise SystemExit("Missing ALLOWED_GUILD_ID")

intents = discord.Intents.default()
intents.members = True
intents.presences = True

class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.started_at = datetime.datetime.utcnow()

    async def setup_hook(self):
        guild = discord.Object(id=ALLOWED_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = Bot()

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

async def guard(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("❌ Not authorized", ephemeral=True)
        return False
    if interaction.guild is None or interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("❌ Wrong server", ephemeral=True)
        return False
    return True

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name=STATUS_TEXT))
    print(f"Ready: {bot.user}")

@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD_ID:
        await guild.leave()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        embed = discord.Embed(
            title="New DM",
            description=message.content or "(No text)",
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_author(
            name=f"{message.author} ({message.author.id})",
            icon_url=message.author.display_avatar.url
        )
        for owner_id in OWNER_IDS:
            try:
                user = await bot.fetch_user(owner_id)
                await user.send(embed=embed)
            except:
                pass

@bot.tree.command(name="help", description="Show commands")
async def help_cmd(interaction: discord.Interaction):
    if not await guard(interaction): return
    embed = discord.Embed(title="Commands")
    embed.add_field(name="/bc_all", value="Broadcast to all")
    embed.add_field(name="/bc_online", value="Broadcast to online only")
    embed.add_field(name="/bc_user", value="Send to one user")
    embed.add_field(name="/status", value="Change status")
    embed.add_field(name="/stats", value="Bot stats")
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def broadcast(interaction, members: List[discord.Member], text: str):
    sent = 0
    await interaction.response.send_message("⏳ Sending...", ephemeral=True)
    for m in members:
        if m.bot: continue
        try:
            await m.send(text)
            sent += 1
            await asyncio.sleep(1)
        except:
            pass
    await interaction.followup.send(f"✅ Sent to {sent} users", ephemeral=True)

@bot.tree.command(name="bc_all", description="Broadcast to all")
async def bc_all(interaction: discord.Interaction, message: str):
    if not await guard(interaction): return
    guild = bot.get_guild(ALLOWED_GUILD_ID)
    await guild.chunk()
    await broadcast(interaction, guild.members, message)

@bot.tree.command(name="bc_online", description="Broadcast to online")
async def bc_online(interaction: discord.Interaction, message: str):
    if not await guard(interaction): return
    guild = bot.get_guild(ALLOWED_GUILD_ID)
    await guild.chunk()
    members = [m for m in guild.members if m.status != discord.Status.offline]
    await broadcast(interaction, members, message)

@bot.tree.command(name="bc_user", description="Send to user")
async def bc_user(interaction: discord.Interaction, user: discord.User, message: str):
    if not await guard(interaction): return
    await user.send(message)
    await interaction.response.send_message("✅ Sent", ephemeral=True)

@bot.tree.command(name="status", description="Change status")
async def status_cmd(interaction: discord.Interaction, text: str):
    if not await guard(interaction): return
    await bot.change_presence(activity=discord.Game(name=text))
    await interaction.response.send_message("✅ Status updated", ephemeral=True)

@bot.tree.command(name="stats", description="Bot stats")
async def stats(interaction: discord.Interaction):
    if not await guard(interaction): return
    uptime = datetime.datetime.utcnow() - bot.started_at
    embed = discord.Embed(title="Stats")
    embed.add_field(name="Uptime", value=str(uptime).split(".")[0])
    embed.add_field(name="Ping", value=f"{int(bot.latency*1000)} ms")
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)
