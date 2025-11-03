import os
import sqlite3
from asyncio import timeout
from email.message import Message

from discord.ext.commands import command
from dotenv import load_dotenv
import discord
from discord import Intents, ApplicationContext, TextChannel, Embed, Color, DMChannel, commands, default_permissions, \
    Guild

load_dotenv()



bot = discord.Bot(intents=Intents.all())

database = sqlite3.connect("data.db")
cursor = database.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    guild_id TEXT,
    name TEXT,
    id INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS roles (
    guild_id TEXT,
    name TEXT,
    id INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS warns (
    guild_id TEXT,
    user INTEGER,
    count INTEGER
)
""")
database.commit()

class TicketView(discord.ui.View):
    @discord.ui.select(
        custom_id="tickets",
        placeholder="Ticket Art",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="General Support",
                description="Allgemeiner Support für alle Probleme",
                emoji="📞"
            ),
            discord.SelectOption(
                label="Bewerbung",
                description="Bewerbe dich für das Team",
                emoji="📜"
            ),
            discord.SelectOption(
                label="Bug/Report",
                description="Melde ein Bug oder eine Person.",
                emoji="📤"
            ),
        ]
    )
    async def callback(self, select, ctx: ApplicationContext):
        await ctx.response.send_message(
            f"Ticket wird für {select.values[0]} geöffnet...", ephemeral=True
        )

        category = ctx.channel.category or discord.utils.get(ctx.guild.categories, name="Tickets")
        channel: TextChannel | None = None
        teamrole: discord.Role = get_role(ctx.guild, "team")

        match select.values[0]:
            case "General Support":
                channel = await category.create_text_channel(f"general-support-{ctx.user.name}")
                perms = channel.overwrites_for(ctx.guild.default_role)
                perms.send_messages = False
                perms.view_channel = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=perms)
                perms = channel.overwrites_for(teamrole)
                perms.send_messages = True
                perms.view_channel = True
                await channel.set_permissions(teamrole, overwrite=perms)
                perms = ctx.channel.overwrites_for(ctx.user)
                perms.send_messages = True
                perms.view_channel = True
                await channel.set_permissions(ctx.user, overwrite=perms)
            case "Bewerbung":
                channel = await category.create_text_channel(f"bewerbung-{ctx.user.name}")
                perms = channel.overwrites_for(ctx.guild.default_role)
                perms.send_messages = False
                perms.view_channel = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=perms)
                perms = channel.overwrites_for(teamrole)
                perms.send_messages = True
                perms.view_channel = True
                await channel.set_permissions(teamrole, overwrite=perms)
                perms = ctx.channel.overwrites_for(ctx.user)
                perms.send_messages = True
                perms.view_channel = True
                await channel.set_permissions(ctx.user, overwrite=perms)
            case "Bug/Report":
                channel = await category.create_text_channel(f"bug-report-{ctx.user.name}")
                perms = channel.overwrites_for(ctx.guild.default_role)
                perms.send_messages = False
                perms.view_channel = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=perms)
                perms = channel.overwrites_for(teamrole)
                perms.send_messages = True
                perms.view_channel = True
                await channel.set_permissions(teamrole, overwrite=perms)
                perms = ctx.channel.overwrites_for(ctx.user)
                perms.send_messages = True
                perms.view_channel = True
                await channel.set_permissions(ctx.user, overwrite=perms)
            case _:
                await ctx.followup.send("Ungültige Auswahl.", ephemeral=True)
                return

        await ctx.followup.send(f"Ticket wurde erstellt: {channel.mention}", ephemeral=True)
        ticketEmbed = Embed(color=Color.random(), title="Ticket",
                            description="Da wir auch nur Menschen sind kann es ein wenig dauern bis du eine Antwort erhälst. Bitte erkläre dein Problem schonmal."
                            )
        await channel.send(embeds=[ticketEmbed], view=TicketCloseView())




class TicketCloseView(discord.ui.View):
    @discord.ui.button(label="Schließen", style=discord.ButtonStyle.danger,
                       emoji="🗑")
    @default_permissions(manage_messages=True)

    async def button_callback(self, button, interaction: ApplicationContext):
       #transcript

       messages = [msg async for msg in interaction.channel.history(limit=None)]
       transcript = "\n".join(f"{msg.author}: {msg.content}" for msg in reversed(messages))
       dmchan: DMChannel = await interaction.user.create_dm()
       embed = Embed(color=Color.random(), title="Ticket geschlossen", description="Dein Transkript kommt gleich!")
       await dmchan.send(embed=embed)
       await dmchan.send(f"```"
                   f"{transcript}"
                   f"```")
       #delete
       await interaction.channel.delete(reason="Ticket closed.")





def get_channel(guild: discord.Guild, name: str) -> discord.TextChannel | None:
    guild_id_str = str(guild.id)
    cursor.execute("SELECT id FROM channels WHERE guild_id = ? AND name = ?", (guild_id_str, name))
    result = cursor.fetchone()
    if result:
        channel_id = result[0]
        return guild.get_channel(channel_id)
    return None




def get_role(guild: discord.Guild, name: str) -> discord.Role | None:
  guild_id_str = str(guild.id)
  cursor.execute("SELECT id FROM roles WHERE guild_id = ? AND name = ?", (guild_id_str, name))
  result = cursor.fetchone()
  if result:
    channel_id = result[0]
    return guild.get_role(channel_id)
  return None

async def check_perms(ctx: ApplicationContext) -> bool:
    if not (ctx.user.roles.__contains__(get_role(name="team", guild=ctx.guild))):
        embed = Embed(
            color=discord.Color.red(),
            title="Uh oh!",
            description="Du hast nicht genügend Rechte dafür!"
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return False
    return True

def get_warns(guild: discord.Guild, user_id: int) -> int:
    guild_id_str = str(guild.id)
    cursor.execute(
        "SELECT count FROM warns WHERE guild_id = ? AND user = ?",
        (guild_id_str, user_id)
    )
    result = cursor.fetchone()
    return result[0] if result else 0

@bot.slash_command(name="setup", description="Sets up the bot.")
async def setup(ctx: ApplicationContext, welcome_channel: TextChannel, ticket_channel: TextChannel, log_channel: TextChannel, team_role: discord.Role, member_role: discord.Role):
    guild_id_str = str(ctx.guild_id)

    cursor.execute("DELETE FROM channels WHERE guild_id = ?", (guild_id_str,))
    cursor.execute("DELETE FROM roles WHERE guild_id = ?", (guild_id_str,))
    cursor.execute("INSERT INTO channels (guild_id, name, id) VALUES (?, ?, ?)", (guild_id_str, "welcome", welcome_channel.id))
    cursor.execute("INSERT INTO channels (guild_id, name, id) VALUES (?, ?, ?)", (guild_id_str, "ticket", ticket_channel.id))
    cursor.execute("INSERT INTO channels (guild_id, name, id) VALUES (?, ?, ?)", (guild_id_str, "log", log_channel.id))
    cursor.execute("INSERT INTO roles (guild_id, name, id) VALUES (?, ?, ?)",(guild_id_str, "team", team_role.id))
    cursor.execute("INSERT INTO roles (guild_id, name, id) VALUES (?, ?, ?)", (guild_id_str, "member", member_role.id))
    database.commit()

    embed = Embed(
        color=Color.green(),
        title="Erfolgreich!",
        description="Du hast den Bot erfolgreich eingerichtet. Habe Spaß!"
    )
    embed.set_footer(text="ThisCord | Setup")
    ticketEmbed = Embed(color=discord.Color.random(), title="Tickets", description="Wenn du Hilfe brauchst musst du einfach nur ein Ticket öffnen! Egal ob du dich bewerben möchtest oder andere Hilfe brauchst!")
    await ticket_channel.send(embed=ticketEmbed, view=TicketView(timeout=None))
    await ctx.respond(embed=embed)


@bot.event
async def on_ready():
    print(f"ThisCord started. Bot name: {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    await member.add_roles(get_role(member.guild, "member"))
    guild_id_str = str(member.guild.id)
    cursor.execute("SELECT id FROM channels WHERE guild_id = ? AND name = ?", (guild_id_str, "welcome"))
    channel = get_channel(member.guild, "welcome")
    logchannel = get_channel(member.guild, "log")
    ca = member.created_at

    if logchannel:
        embed = Embed(color=discord.Color.random(), title="Neuer Member")
        embed.add_field(name="Name", value=member.name, inline=False)
        embed.add_field(name="Account Alter", value=ca.strftime("%d %A %B %Y"), inline=False)
        embed.set_image(url=member.display_avatar.url)
        await logchannel.send(embed=embed)
    if channel:
        embed = Embed(color=discord.Color.random(), title="Willkommen!", description=f"Willkommen, {member.mention}! Wir hoffen das du eine schöne Zeit haben wirst!")
        embed.set_image(url=member.display_avatar.url)
        await channel.send(embeds=[embed])


class FakeNitroView(discord.ui.View):
    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple)
    async def callback(self, button:discord.Button, interaction: ApplicationContext):
        await interaction.response.send_message("https://tenor.com/view/rickroll-roll-rick-never-gonna-give-you-up-never-gonna-gif-22954713", ephemeral=True)
        button.disabled = True
        button.__setattr__("label", "Already claimed")


@bot.slash_command(name="nitrogen", description="Generiert kostenloses Nitro!")
async def nitrogen(ctx: ApplicationContext):
    embed = Embed(color=Color.blurple(), title="Dir wurde etwas geschenkt!", description="Dir wurde ein Nitro Abbonement geschenkt!",)
    embed.set_image(url="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Ftse4.mm.bing.net%2Fth%2Fid%2FOIP.qSLk7_TjbqrDhTzK3KMcBgHaEK%3Fpid%3DApi&f=1&ipt=5ec06c5bb8c5a56f39aba8eb0840e7f29a296fd13c2af50f3c697bee6baf7cb3&ipo=images")
    await ctx.response.send_message(embed=embed, view=FakeNitroView())

@bot.event
async def on_guild_join(guild: Guild):
    owner = guild.owner
    channel = await owner.create_dm()
    embed = Embed(color=Color.random(), title="Danke!",
                  description="Ich danke dir echt daß du unseren Bot nutzt! Es heißt so viel zu mir! Falls du diesen nicht eingeladen hast, erkundige dich bei einem der Teammitglieder.",
                  )
    await channel.send(embed=embed)

@bot.slash_command(name="warn", description="Warne einen Nutzer")
async def warn(ctx: ApplicationContext, user: discord.Member):
    if not await check_perms(ctx):
        return
    guild_id_str = str(ctx.guild_id)
    count = get_warns(ctx.guild, user.id)
    new_count = count + 1

    if count == 0:
        cursor.execute(
            "INSERT INTO warns (guild_id, user, count) VALUES (?, ?, ?)",
            (guild_id_str, user.id, new_count)
        )
    else:
        cursor.execute(
            "UPDATE warns SET count = ? WHERE guild_id = ? AND user = ?",
            (new_count, guild_id_str, user.id)
        )

    database.commit()

    embed = Embed(
        color=discord.Color.orange(),
        title="Verwarnt ✅",
        description=f"{user.mention} wurde verwarnt!"
    )
    embed.add_field(name="Warns vorher", value=str(count))
    embed.add_field(name="Warns jetzt", value=str(new_count))
    await ctx.respond(embed=embed)

    dmchannel: DMChannel = await user.create_dm()
    dmEmbed = Embed(
        color=discord.Color.orange(),
        title="Verwarnt",
        description=f"**Du wurdest verwarnt!**"
    )

    dmEmbed.add_field(name="Server", value=ctx.guild.name, inline=False)
    dmEmbed.add_field(name="Moderator", value=f"{ctx.user.display_name} ({ctx.user.name})", inline=False)
    dmEmbed.add_field(name="Anzahl", value=new_count, inline=False)

    await dmchannel.send(embed=dmEmbed)


@bot.slash_command(name="warns", description="Checke die Warns eines Nutzers")
async def warns(ctx: ApplicationContext, user: discord.Member):
    if not await check_perms(ctx):
        return
    count = get_warns(ctx.guild, user.id)
    embed = Embed(
        color=discord.Color.random(),
        title=f"Warns von {user.name}",
        description=f"Dieser Nutzer hat **{count}** Verwarnung(en)."
    )
    await ctx.respond(embed=embed)


@bot.slash_command(name="ban", description="Banne einen Nutzer vom Server")
@default_permissions(ban_members=True)
async def ban(ctx: ApplicationContext, user: discord.Member, reason: str):
    if not await check_perms(ctx):
        return
    try:
        await user.ban(reason=reason)
    except:
        embed = Embed(
            color=discord.Color.red(),
            title="Fehler!",
            description="Ein Fehler ist passiert! (Der Bot hat wahrscheinlich nicht ausreichende Rechte)"
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    embed = Embed(
        color=discord.Color.random(),
        title="Gebannt ✅",
        description="Erfolgreich gebannt!"
    )
    embed.add_field(name="User", value=f"{user.display_name} ({user.name})", inline=False)
    embed.add_field(name="Grund", value=reason, inline=False)
    await ctx.response.send_message(embed=embed)
    dmchannel: DMChannel = await user.create_dm()
    dmEmbed = Embed(
        color=discord.Color.orange(),
        title="Gebannt",
        description=f"**Du wurdest gebannt!**"
    )

    dmEmbed.add_field(name="Server", value=ctx.guild.name, inline=False)
    dmEmbed.add_field(name="Moderator", value=f"{ctx.user.display_name} ({ctx.user.name})", inline=False)
    dmEmbed.add_field(name="Grund", value=reason, inline=False)
    await dmchannel.send(embed=dmEmbed)

@bot.slash_command(name="kick", description="Kicke einen Nutzer vom Server")
@default_permissions(kick_members=True)
async def kick(ctx: ApplicationContext, user: discord.Member, reason: str):
    if not await check_perms(ctx):
        return
    try:
        await user.kick(reason=reason)
    except:
        embed = Embed(
            color=discord.Color.red(),
            title="Fehler!",
            description="Ein Fehler ist passiert! (Der Bot hat wahrscheinlich nicht ausreichende Rechte)"
        )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        return
    embed = Embed(
        color=discord.Color.random(),
        title="Kicked ✅",
        description="Erfolgreich gekickt!"
    )
    embed.add_field(name="User", value=f"{user.display_name} ({user.name})", inline=False)
    embed.add_field(name="Grund", value=reason, inline=False)
    await ctx.response.send_message(embed=embed)
    dmchannel: DMChannel = await user.create_dm()
    dmEmbed = Embed(
        color=discord.Color.orange(),
        title="Kicked",
        description=f"**Du wurdest gekickt!**"
    )

    dmEmbed.add_field(name="Server", value=ctx.guild.name, inline=False)
    dmEmbed.add_field(name="Moderator", value=f"{ctx.user.display_name} ({ctx.user.name})", inline=False)
    dmEmbed.add_field(name="Grund", value=reason, inline=False)
    await dmchannel.send(embed=dmEmbed)


@bot.event
async def on_close():
    database.close()

@bot.slash_command(name="clearchat", description="Clear den Chat!")
async def clearchat(ctx: ApplicationContext):
    channel_new: TextChannel = await ctx.channel.clone()
    embed=Embed(
        title="Erfolgreich",
        color=discord.Color.random(),
        description="Erfolgreich gecleart."
    )
    await channel_new.send(embed=embed)


bot.run(os.getenv("TOKEN"))
